import os
import glob
import uuid
import atexit
import tempfile

def get_temp_audio_path(prefix="jarvis_audio_", suffix=".mp3") -> str:
    """Generates a unique path in the OS temp folder without creating an open file lock."""
    temp_dir = tempfile.gettempdir()
    unique_name = f"{prefix}{uuid.uuid4().hex[:8]}{suffix}"
    return os.path.join(temp_dir, unique_name)

def cleanup_orphaned_audio():
    """Sweeps and deletes any leftover jarvis_* audio files in the OS temp directory."""
    temp_dir = tempfile.gettempdir()
    patterns = ["jarvis_audio_*", "jarvis_mic_input_*", "jarvis_tts_*"]
    removed_count = 0
    for pattern in patterns:
        for file_path in glob.glob(os.path.join(temp_dir, pattern)):
            try:
                os.remove(file_path)
                removed_count += 1
            except OSError:
                pass
    if removed_count > 0:
        print(f"[System Cleanup]: Removed {removed_count} orphaned temp audio file(s).")

# Automatically run cleanup on startup and normal interpreter exit
cleanup_orphaned_audio()
atexit.register(cleanup_orphaned_audio)