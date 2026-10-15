import os
import shutil
import tempfile
import uuid
import pydub
from pathlib import Path


class AudioUtils:
    @staticmethod
    def get_safe_path(original_path: str) -> str:
        """
        Creates a safe temporary path for files with non-standard characters
        (like Chinese characters or spaces) or deep folder structures to prevent
        C++ layer crashes.
        """
        original_path = Path(original_path)
        if not original_path.exists():
            raise FileNotFoundError(f"找不到文件: {original_path}")

        # Create a unique, safe temporary file name in the temp directory
        safe_filename = f"{uuid.uuid4().hex}{original_path.suffix}"
        safe_path = Path(tempfile.gettempdir()) / safe_filename

        # Copy the file to the safe path
        shutil.copy2(original_path, safe_path)
        return str(safe_path)

    @staticmethod
    def get_metadata(filepath: str) -> dict:
        """
        Extracts audio metadata: duration (seconds), file size (bytes),
        channels, and format.
        """
        filepath_obj = Path(filepath)
        if not filepath_obj.exists():
            raise FileNotFoundError(f"找不到文件: {filepath}")

        file_size = filepath_obj.stat().st_size
        audio_format = filepath_obj.suffix.lower().lstrip('.')

        try:
            audio = pydub.AudioSegment.from_file(filepath)
            duration = len(audio) / 1000.0  # pydub length is in milliseconds
            channels = audio.channels
        except Exception as e:
            # Fallback if pydub fails
            duration = 0.0
            channels = 0
            print(f"提取元数据时出错: {e}")

        return {
            "duration": duration,
            "file_size": file_size,
            "channels": channels,
            "format": audio_format,
        }
