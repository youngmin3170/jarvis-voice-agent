import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from tools import ALL_TOOLS

from tools.voice import speak
from tools.listen import transcribe_speech
from tools.wakeword import wait_for_wake_word

# Load environment variables
load_dotenv()

# Initialize Gemini Client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_FLASH = "gemini-3.5-flash-lite"

# Load system instructions from prompt.md if it exists
if os.path.exists("prompt.md"):
    with open("prompt.md", "r", encoding="utf-8") as f:
        system_prompt = f.read()

# Register external tools and system persona
chat = client.chats.create(
    model=MODEL_FLASH,
    config=types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=ALL_TOOLS
    )
)

print("J.A.R.V.I.S. Online. Modular Architecture Active.")
print("-" * 60)

while True:
    # Standby Mode: Wait for "Hey Jarvis"
    wait_for_wake_word()

    speak("Yes, sir?")
    
    # Active Session Mode: Keep listening for follow-up questions
    while True:
        user_query = transcribe_speech()

        # If 5 seconds of silence pass, exit active session back to Standby Mode
        if not user_query:
            print("[J.A.R.V.I.S.]: No follow-up detected. Returning to standby mode.")
            break

        # Check for shutdown commands
        if user_query.lower().strip(".!?") in ['quit', 'exit', 'bye', 'goodbye', '종료', '꺼져']:
            print("J.A.R.V.I.S.: Systems offline.")
            speak("Systems offline. Goodbye, sir.")
            exit(0)
            
        try:
            response = chat.send_message(user_query)
            print(f"\nJ.A.R.V.I.S.: {response.text}")
            speak(response.text)
        except Exception as e:
            print(f"\n[System Error]: {e}")
            break