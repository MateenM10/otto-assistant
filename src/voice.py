"""
Reusable voice input: record from the mic, transcribe with Whisper.

Recording now stops when you press Enter again, instead of waiting a
fixed number of seconds — feels much snappier for short questions.
"""

import sounddevice as sd
import numpy as np
import wave
import threading
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000
RECORDING_PATH = "temp_recording.wav"

print("Loading speech recognition model...")
_model = WhisperModel("base", device="cpu", compute_type="int8")
print("Ready.")


def listen() -> str:
    """Record from the mic until the user presses Enter again, then transcribe."""
    print("Listening... (press Enter when you're done talking)")

    chunks = []

    def callback(indata, frames, time_info, status):
        chunks.append(indata.copy())

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        callback=callback,
    )

    with stream:
        input()  # blocks here until Enter is pressed again

    if not chunks:
        return ""

    recording = np.concatenate(chunks, axis=0)

    with wave.open(RECORDING_PATH, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        f.writeframes(recording.tobytes())

    segments, _ = _model.transcribe(RECORDING_PATH)
    return " ".join(segment.text for segment in segments).strip()