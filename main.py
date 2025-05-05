import os
from dotenv import load_dotenv
import sounddevice as sd
import numpy as np
import requests
import tempfile
import wave
import time
import pyautogui
from pynput import keyboard

# Load environment variables
load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("VOICE_MODEL")


def save_wav(audio, fs):
    # Save audio to a temporary WAV file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmpfile:
        with wave.open(tmpfile, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit audio
            wf.setframerate(fs)
            wf.writeframes(audio.tobytes())
        return tmpfile.name

def transcribe(audio, fs):
    wav_path = save_wav(audio, fs)
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    data = {
        "model": MODEL,
        "language": "en"
    }
    try:
        with open(wav_path, "rb") as f:
            files = {
                "file": (os.path.basename(wav_path), f, "audio/wav"),
            }
            response = requests.post(url, headers=headers, files=files, data=data)
        # File is now closed, safe to remove
        for _ in range(5):
            try:
                os.remove(wav_path)
                break
            except PermissionError:
                time.sleep(0.1)
        if response.ok:
            return response.json().get("text", "")
        else:
            print("Error:", response.text)
            return ""
    except Exception as e:
        print(f"Exception during transcription: {e}")
        if os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except Exception:
                pass
        return ""

def main():
    print("Hold SHIFT key to record, release to transcribe and type at cursor...")
    fs = 16000
    
    # Create a listener for key press/release events
    shift_pressed = False
    audio = []
    recording = False
    listener = None
    
    def on_press(key):
        nonlocal shift_pressed, audio, recording
        # Check if pressed key is shift
        if key == keyboard.Key.shift or key == keyboard.Key.shift_r:
            if not shift_pressed:
                shift_pressed = True
                print("Listening... (release SHIFT to stop)")
                audio = []
                recording = True
                
                # Start recording in a separate thread to avoid blocking
                def record_audio():
                    nonlocal audio, recording
                    def callback(indata, frames, time_info, status):
                        if recording:
                            audio.append(indata.copy())
                    
                    with sd.InputStream(samplerate=fs, channels=1, dtype='int16', callback=callback):
                        while recording:
                            sd.sleep(50)
                
                import threading
                recording_thread = threading.Thread(target=record_audio)
                recording_thread.daemon = True
                recording_thread.start()
    
    def on_release(key):
        nonlocal shift_pressed, audio, recording
        # Check if released key is shift
        if key == keyboard.Key.shift or key == keyboard.Key.shift_r:
            if shift_pressed:
                shift_pressed = False
                recording = False
                print("Transcribing...")
                if audio:
                    audio_np = np.concatenate(audio, axis=0)
                    text = transcribe(audio_np, fs)
                    print("You said:", text)
                    if text.strip():
                        print("Typing at cursor...")
                        pyautogui.typewrite(text)
                else:
                    print("No audio captured.")
    
    # Start the listener
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()  # Keep the listener running

if __name__ == "__main__":
    main() 