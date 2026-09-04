"""
Voice input test: record a few seconds of audio from the microphone,
save it to a file, then transcribe it to text with Whisper. This
proves both halves of speech-to-text work before we wire it into
the real assistant.
"""

import sounddevice as sd
import numpy as np
import wave
from faster_whisper import WhisperModel

DURATION_SECONDS = 4
SAMPLE_RATE = 16000  # Whisper expects 16kHz audio

# --- Step 1: Record from the microphone ---
print(f"Recording for {DURATION_SECONDS} seconds... speak now!")
recording = sd.rec(
    int(DURATION_SECONDS * SAMPLE_RATE),
    samplerate=SAMPLE_RATE,
    channels=1,
    dtype="int16",
)
sd.wait()  # blocks until recording is finished
print("Done recording.")

with wave.open("test_recording.wav", "wb") as f:
    f.setnchannels(1)
    f.setsampwidth(2)  # 2 bytes = 16-bit audio
    f.setframerate(SAMPLE_RATE)
    f.writeframes(recording.tobytes())

print("Saved to test_recording.wav")

# --- Step 2: Transcribe it with Whisper ---
print("Loading Whisper model (first run downloads it, may take a minute)...")
model = WhisperModel("base", device="cpu", compute_type="int8")

print("Transcribing...")
segments, info = model.transcribe("test_recording.wav")

text = " ".join(segment.text for segment in segments).strip()
print(f"\nYou said: {text}")