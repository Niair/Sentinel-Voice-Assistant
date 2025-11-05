import os
import io
from typing import Optional, Union
import whisper
import speech_recognition as sr
from pydub import AudioSegment
from ..config import Config

class STTClient:
    """
    Speech-to-Text client supporting Hinglish (Hindi + English).
    Uses OpenAI Whisper for local transcription.
    """
    
    def __init__(self, model_size: str = "base"):
        """
        Initialize STT client.
        
        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
                       - tiny: fastest, least accurate
                       - base: good balance for real-time
                       - medium/large: most accurate but slower
        """
        self.model_size = model_size
        self.model = None
        self.recognizer = sr.Recognizer()
        
    def load_model(self):
        """Lazy load Whisper model to save memory."""
        if self.model is None:
            self.model = whisper.load_model(self.model_size)
    
    def transcribe_audio_file(
        self, 
        audio_path: str,
        language: Optional[str] = None
    ) -> dict:
        """
        Transcribe audio file to text.
        
        Args:
            audio_path: Path to audio file (mp3, wav, m4a, etc.)
            language: Optional language hint (e.g., 'hi' for Hindi, 'en' for English)
                     Leave None for auto-detection (works well for Hinglish)
        
        Returns:
            Dict with transcription text and metadata
        """
        self.load_model()
        
        try:
            # Whisper supports multiple audio formats
            result = self.model.transcribe(
                audio_path,
                language=language,
                task="transcribe",
                fp16=False  # Set to True if using GPU
            )
            
            return {
                "text": result["text"].strip(),
                "language": result.get("language", "unknown"),
                "segments": result.get("segments", [])
            }
        except Exception as e:
            raise Exception(f"STT transcription error: {str(e)}")
    
    def transcribe_audio_bytes(
        self, 
        audio_bytes: bytes,
        format: str = "wav",
        language: Optional[str] = None
    ) -> dict:
        """
        Transcribe audio from bytes.
        
        Args:
            audio_bytes: Audio data as bytes
            format: Audio format (wav, mp3, etc.)
            language: Optional language hint
        
        Returns:
            Dict with transcription text and metadata
        """
        self.load_model()
        
        try:
            # Convert bytes to audio file
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format=format)
            
            # Export to temporary WAV for Whisper
            temp_path = "temp_audio.wav"
            audio.export(temp_path, format="wav")
            
            result = self.transcribe_audio_file(temp_path, language)
            
            # Cleanup
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            return result
        except Exception as e:
            raise Exception(f"STT bytes transcription error: {str(e)}")
    
    def transcribe_microphone(
        self, 
        duration: int = 5,
        language: Optional[str] = None
    ) -> dict:
        """
        Record and transcribe from microphone.
        
        Args:
            duration: Recording duration in seconds
            language: Optional language hint
        
        Returns:
            Dict with transcription text and metadata
        """
        try:
            with sr.Microphone() as source:
                print(f"Recording for {duration} seconds...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                audio = self.recognizer.record(source, duration=duration)
            
            # Save to temp file
            temp_path = "temp_mic.wav"
            with open(temp_path, "wb") as f:
                f.write(audio.get_wav_data())
            
            result = self.transcribe_audio_file(temp_path, language)
            
            # Cleanup
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            return result
        except Exception as e:
            raise Exception(f"Microphone transcription error: {str(e)}")
    
    def health_check(self) -> bool:
        """
        Check if STT service is working.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            self.load_model()
            return self.model is not None
        except:
            return False
