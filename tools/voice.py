import os
import asyncio
import pygame
import edge_tts
from elevenlabs.client import ElevenLabs
from utils import get_temp_audio_path

pygame.mixer.init()

def speak(text: str):
    """
    Primary: ElevenLabs
    Fallback: edge-tts
    """
    eleven_key = os.getenv("ELEVENLABS_API_KEY")
    
    # prevents the "text must be str" error in edge-tts.
    safe_text = str(text).strip()
    
    if not safe_text:
        return
    
    if eleven_key:
        try:
            print("\n[System Audio]: (Generating voice via ElevenLabs...)")
            client = ElevenLabs(api_key=eleven_key)
            
            audio_stream = client.text_to_speech.convert(
                text=safe_text,
                voice_id="nPczCjzI2devNBz1zQrb",
                model_id="eleven_flash_v2_5" 
            )
            
            _save_and_play_eleven_audio(audio_stream)
            return

        except KeyboardInterrupt:
            print("\n[J.A.R.V.I.S.]: Voice generation cancelled by user.")
            return
        
        except Exception as e:
            print(f"\n[System Warning]: ElevenLabs out of quota or failed ({e}). Executing fallback...")
            
    # Fallback triggers if ElevenLabs crashes, runs out of credits, or the key is missing
    _edge_tts_fallback(safe_text)


def _save_and_play_eleven_audio(audio_generator):
    """
    Helper to save ElevenLabs audio bytes to a temp file and play it.
    """
    temp_path = get_temp_audio_path()

    try:
        with open(temp_path, "wb") as f:
            for chunk in audio_generator:
                if chunk:
                    f.write(chunk)
                    
        _play_file(temp_path)
    finally:
        _safe_delete(temp_path)


def _edge_tts_fallback(text: str):
    """Helper fallback handler using free edge-tts."""
    print("\n[System Audio]: (Generating voice via edge-tts...)")
    temp_path = get_temp_audio_path()
    
    try:
        async def generate_edge():
            communicate = edge_tts.Communicate(text, "en-GB-ThomasNeural")
            await communicate.save(temp_path)
            
        asyncio.run(generate_edge())
        _play_file(temp_path)

    except KeyboardInterrupt:
        print("\n[J.A.R.V.I.S.]: Speech interrupted by user.")

    except Exception as e:
        print(f"[System Error]: Fallback TTS failed: {e}")

    finally:
        _safe_delete(temp_path)


def _play_file(file_path: str):
    """
    Plays an mp3 file via Pygame and deletes it afterward to keep your computer clean.
    """

    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        print(f"[System Error]: Audio file was not created properly at '{file_path}'.")
        return

    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        
        # Keep the script paused while speaking
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
            
    except KeyboardInterrupt:
        print("\n[J.A.R.V.I.S.]: Speech interrupted! Stopping audio...")
    except Exception as e:
        print(f"[System Error]: Audio playback failed: {e}")
    finally:
        # Clean up the temporary audio file safely
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
        except Exception:
            pass

        _safe_delete(file_path)


def _safe_delete(file_path: str):
    """Deletes a file if it exists, logging a warning if Windows still locks it."""
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError as e:
            print(f"[System Warning]: Could not delete temp file {file_path}: {e}")