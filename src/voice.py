import threading
import wave

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000
RECORDING_PATH = "temp_recording.wav"

print("Loading speech recognition model...")
_model = WhisperModel("base", device="cpu", compute_type="int8")
print("Ready.")

_stop_recording = threading.Event()


def request_stop() -> None:
    """Signal an in-progress recording to finish. Called by the HUD."""
    _stop_recording.set()


def listen() -> str:
    """Record until request_stop() is called, then transcribe."""
    _stop_recording.clear()
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
        # Wake up periodically rather than blocking forever, so a
        # Ctrl+C in the terminal can still interrupt.
        while not _stop_recording.wait(timeout=0.1):
            pass

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