import pyaudio
import numpy as np
import openwakeword
from openwakeword.model import Model

def wait_for_wake_word(threshold=0.5):
    """
    Blocks execution and listens continuously using openWakeWord 
    until the wake word is detected.
    """
    print("[System Init]: Loading openWakeWord models...")

    oww_model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")

    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    CHUNK = 1280

    audio = pyaudio.PyAudio()
    mic_stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )

    print("\n[J.A.R.V.I.S.]: Standby mode active. Waiting for wake word ('Hey Jarvis')...")

    try:
        while True:
            # Read raw audio from the microphone
            audio_data = mic_stream.read(CHUNK, exception_on_overflow=False)
            # Convert to a numpy array for openWakeWord
            audio_np = np.frombuffer(audio_data, dtype=np.int16)

            # Feed the audio chunk to the model
            prediction = oww_model.predict(audio_np)

            # prediction is a dictionary of scores e.g., {'hey_jarvis': 0.85}
            for model_name, score in prediction.items():
                if score >= threshold:
                    print(f"\n[System]: Wake word '{model_name}' detected! Waking up...")
                    return # Exit the function, allowing main.py to trigger Whisper!

    except Exception as e:
        print(f"[System Error]: Wake word engine failed: {e}")
        
    finally:
        # Clean up the audio stream to hand the microphone over to Whisper
        mic_stream.stop_stream()
        mic_stream.close()
        audio.terminate()