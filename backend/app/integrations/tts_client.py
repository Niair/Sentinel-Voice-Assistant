import os
from typing import Optional
from elevenlabs import generate, set_api_key, Voice, VoiceSettings
from ..config import Config

class TTSClient:
    """
    Text-to-Speech client using ElevenLabs API.
    Supports multiple voices and languages including Hindi.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize TTS client.
        
        Args:
            api_key: ElevenLabs API key (defaults to config)
        """
        self.api_key = api_key or Config.ELEVENLABS_API_KEY
        
        if not self.api_key:
            raise ValueError("ElevenLabs API key not provided")
        
        set_api_key(self.api_key)
        
        # Default voice settings
        self.default_voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
        self.voice_settings = VoiceSettings(
            stability=0.5,
            similarity_boost=0.75,
            style=0.0,
            use_speaker_boost=True
        )
    
    def generate_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model: str = "eleven_multilingual_v2",
        output_path: Optional[str] = None
    ) -> bytes:
        """
        Generate speech from text.
        
        Args:
            text: Text to convert to speech
            voice_id: ElevenLabs voice ID (uses default if not provided)
            model: Model to use (eleven_multilingual_v2 supports Hindi)
            output_path: Optional path to save audio file
        
        Returns:
            Audio data as bytes
        """
        try:
            voice_id = voice_id or self.default_voice_id
            
            audio = generate(
                text=text,
                voice=voice_id,
                model=model,
                voice_settings=self.voice_settings
            )
            
            # Convert generator to bytes
            audio_bytes = b''.join(audio)
            
            # Save to file if path provided
            if output_path:
                with open(output_path, 'wb') as f:
                    f.write(audio_bytes)
            
            return audio_bytes
            
        except Exception as e:
            raise Exception(f"TTS generation error: {str(e)}")
    
    def generate_speech_stream(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model: str = "eleven_multilingual_v2"
    ):
        """
        Generate speech as a stream (for real-time playback).
        
        Args:
            text: Text to convert to speech
            voice_id: ElevenLabs voice ID (uses default if not provided)
            model: Model to use
        
        Yields:
            Audio chunks as bytes
        """
        try:
            voice_id = voice_id or self.default_voice_id
            
            audio_stream = generate(
                text=text,
                voice=voice_id,
                model=model,
                voice_settings=self.voice_settings,
                stream=True
            )
            
            for chunk in audio_stream:
                yield chunk
                
        except Exception as e:
            raise Exception(f"TTS streaming error: {str(e)}")
    
    def set_voice(self, voice_id: str):
        """
        Set the default voice.
        
        Args:
            voice_id: ElevenLabs voice ID
        """
        self.default_voice_id = voice_id
    
    def set_voice_settings(
        self,
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0
    ):
        """
        Update voice settings.
        
        Args:
            stability: Voice stability (0.0 - 1.0)
            similarity_boost: Similarity boost (0.0 - 1.0)
            style: Style exaggeration (0.0 - 1.0)
        """
        self.voice_settings = VoiceSettings(
            stability=stability,
            similarity_boost=similarity_boost,
            style=style,
            use_speaker_boost=True
        )
    
    def health_check(self) -> bool:
        """
        Check if ElevenLabs API is accessible.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try generating a very short audio
            test_audio = generate(
                text="test",
                voice=self.default_voice_id,
                model="eleven_multilingual_v2"
            )
            # Convert generator to bytes to actually make the API call
            _ = b''.join(test_audio)
            return True
        except:
            return False


# Popular ElevenLabs voice IDs for reference:
VOICE_IDS = {
    "rachel": "21m00Tcm4TlvDq8ikWAM",  # American female
    "drew": "29vD33N1CtxCmqQRPOHJ",     # American male
    "clyde": "2EiwWnXFnvU5JabPnv8n",    # American male
    "paul": "5Q0t7uMcjvnagumLfvZi",     # American male
    "domi": "AZnzlk1XvdvUeBnXmlld",     # American female
    "bella": "EXAVITQu4vr4xnSDxMaL",    # American female
    "antoni": "ErXwobaYiN019PkySvjV",   # American male
    "elli": "MF3mGyEYCl7XYWbV9V6O",     # American female
    "josh": "TxGEqnHWrfWFTfGW9XjX",     # American male
    "arnold": "VR6AewLTigWG4xSOukaG",   # American male
    "adam": "pNInz6obpgDQGcFmaJgB",     # American male
    "sam": "yoZ06aMxZJJ28mfd3POQ",      # American male
}
