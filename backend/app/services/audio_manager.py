import os
import uuid
from typing import Optional, Tuple
from datetime import datetime
from pydub import AudioSegment
import base64

class AudioManager:
    """
    Manages audio file storage, processing, and format conversion.
    """
    
    def __init__(self, storage_dir: str = "./data/audio"):
        """
        Initialize audio manager.
        
        Args:
            storage_dir: Directory to store audio files
        """
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        
        # Create subdirectories
        self.input_dir = os.path.join(storage_dir, "input")
        self.output_dir = os.path.join(storage_dir, "output")
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
    
    def save_audio_file(
        self,
        audio_data: bytes,
        file_extension: str = "wav",
        subfolder: str = "input"
    ) -> str:
        """
        Save audio data to file.
        
        Args:
            audio_data: Audio file bytes
            file_extension: File extension (wav, mp3, etc.)
            subfolder: Subfolder to save to (input/output)
        
        Returns:
            Full path to saved file
        """
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{timestamp}_{unique_id}.{file_extension}"
        
        # Determine save directory
        save_dir = self.input_dir if subfolder == "input" else self.output_dir
        filepath = os.path.join(save_dir, filename)
        
        # Save file
        with open(filepath, 'wb') as f:
            f.write(audio_data)
        
        return filepath
    
    def load_audio_file(self, filepath: str) -> bytes:
        """
        Load audio file as bytes.
        
        Args:
            filepath: Path to audio file
        
        Returns:
            Audio file bytes
        """
        with open(filepath, 'rb') as f:
            return f.read()
    
    def convert_audio_format(
        self,
        input_path: str,
        output_format: str = "wav",
        sample_rate: Optional[int] = None,
        channels: Optional[int] = None
    ) -> str:
        """
        Convert audio file to different format.
        
        Args:
            input_path: Path to input audio file
            output_format: Target format (wav, mp3, ogg, etc.)
            sample_rate: Target sample rate (Hz)
            channels: Number of channels (1 for mono, 2 for stereo)
        
        Returns:
            Path to converted file
        """
        # Load audio
        audio = AudioSegment.from_file(input_path)
        
        # Apply transformations
        if sample_rate:
            audio = audio.set_frame_rate(sample_rate)
        if channels:
            audio = audio.set_channels(channels)
        
        # Generate output path
        base_name = os.path.basename(input_path)
        name_without_ext = os.path.splitext(base_name)[0]
        output_filename = f"{name_without_ext}_converted.{output_format}"
        output_path = os.path.join(self.output_dir, output_filename)
        
        # Export
        audio.export(output_path, format=output_format)
        
        return output_path
    
    def get_audio_duration(self, filepath: str) -> float:
        """
        Get duration of audio file in seconds.
        
        Args:
            filepath: Path to audio file
        
        Returns:
            Duration in seconds
        """
        audio = AudioSegment.from_file(filepath)
        return len(audio) / 1000.0  # Convert ms to seconds
    
    def trim_audio(
        self,
        filepath: str,
        start_ms: int = 0,
        end_ms: Optional[int] = None
    ) -> str:
        """
        Trim audio file.
        
        Args:
            filepath: Path to audio file
            start_ms: Start time in milliseconds
            end_ms: End time in milliseconds (None for end of file)
        
        Returns:
            Path to trimmed file
        """
        audio = AudioSegment.from_file(filepath)
        
        if end_ms is None:
            trimmed = audio[start_ms:]
        else:
            trimmed = audio[start_ms:end_ms]
        
        # Generate output path
        base_name = os.path.basename(filepath)
        name_without_ext = os.path.splitext(base_name)[0]
        output_filename = f"{name_without_ext}_trimmed.wav"
        output_path = os.path.join(self.output_dir, output_filename)
        
        trimmed.export(output_path, format="wav")
        
        return output_path
    
    def encode_audio_base64(self, filepath: str) -> str:
        """
        Encode audio file as base64 string.
        
        Args:
            filepath: Path to audio file
        
        Returns:
            Base64 encoded string
        """
        with open(filepath, 'rb') as f:
            audio_bytes = f.read()
        return base64.b64encode(audio_bytes).decode('utf-8')
    
    def decode_audio_base64(
        self,
        base64_string: str,
        output_format: str = "wav"
    ) -> str:
        """
        Decode base64 audio string and save to file.
        
        Args:
            base64_string: Base64 encoded audio
            output_format: Output file format
        
        Returns:
            Path to decoded file
        """
        audio_bytes = base64.b64decode(base64_string)
        return self.save_audio_file(audio_bytes, output_format, "input")
    
    def cleanup_old_files(self, days: int = 7):
        """
        Delete audio files older than specified days.
        
        Args:
            days: Files older than this many days will be deleted
        """
        import time
        current_time = time.time()
        max_age = days * 86400  # Convert days to seconds
        
        for directory in [self.input_dir, self.output_dir]:
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                
                if os.path.isfile(filepath):
                    file_age = current_time - os.path.getmtime(filepath)
                    
                    if file_age > max_age:
                        os.remove(filepath)
                        print(f"Deleted old audio file: {filename}")
    
    def get_audio_info(self, filepath: str) -> dict:
        """
        Get detailed information about audio file.
        
        Args:
            filepath: Path to audio file
        
        Returns:
            Dict with audio metadata
        """
        audio = AudioSegment.from_file(filepath)
        
        return {
            "duration_seconds": len(audio) / 1000.0,
            "channels": audio.channels,
            "sample_rate": audio.frame_rate,
            "sample_width": audio.sample_width,
            "frame_count": audio.frame_count(),
            "file_size_bytes": os.path.getsize(filepath)
        }
