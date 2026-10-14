import os
import tempfile
import uuid


def get_temp_audio_path(prefix: str = "jarvis_tts_", suffix: str = ".mp3") -> str:
    """
    Return a collision-safe audio path in the OS temp directory.
    """
    unique_filename = f"{prefix}{uuid.uuid4().hex}{suffix}"
    return os.path.join(tempfile.gettempdir(), unique_filename)
