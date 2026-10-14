import os
import speech_recognition as sr
from faster_whisper import WhisperModel
from utils import get_temp_audio_path

# Initialize the Whisper model once when the script starts
print("[System Init]: Loading Whisper STT model (this takes a moment on first run)...")

model = WhisperModel("small", device="cpu", compute_type="int8")

def transcribe_speech() -> str:
    """
    Activates the microphone, listens for speech, and transcribes it locally using Whisper.
    Returns the transcribed text as a string.
    """
    recognizer = sr.Recognizer()
    
    # Allow 1.5 seconds of pause before cutting off slow speech
    recognizer.pause_threshold = 1.5
    
    with sr.Microphone() as source:
        print("\n[J.A.R.V.I.S.]: Listening... (Speak now)")
        
        # Calibrate to ambient room noise
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        
        # Enforce a minimum floor so quiet room/cafe hum doesn't trigger recording
        if recognizer.energy_threshold < 500:
            recognizer.energy_threshold = 500
        
        try:
            audio_data = recognizer.listen(source, timeout=5, phrase_time_limit=15)
        except sr.WaitTimeoutError:
            return ""  # Returned if you don't say anything within 5 seconds
            
    print("[J.A.R.V.I.S.]: Processing audio...")
    
    temp_wav = get_temp_audio_path(prefix="jarvis_mic_input_", suffix=".wav")
    
    with open(temp_wav, "wb") as f:
        f.write(audio_data.get_wav_data())
        
    try:
        # Transcribe with Silero VAD enabled to ignore non-speech background noise
        segments, _ = model.transcribe(
            temp_wav, 
            beam_size=5,
            initial_prompt="안녕하세요 자비스. 한국어와 English 대화입니다. Hello Jarvis.",
            condition_on_previous_text=False,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            no_speech_threshold=0.6
        )
        
        transcription = " ".join([segment.text for segment in segments]).strip()
        
        if transcription:
            print(f"You (Spoken): {transcription}")
        else:
            print("[J.A.R.V.I.S.]: (Ignored background noise)")
            
        return transcription
        
    except Exception as e:
        print(f"[System Error]: Transcription failed: {e}")
        return ""
    finally:
        if os.path.exists(temp_wav):
            try:
                os.remove(temp_wav)
            except Exception:
                pass