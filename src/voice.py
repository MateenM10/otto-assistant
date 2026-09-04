import sounddevice as sd
import wave
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000
RECORDING_PATH = "temp_recording.wav"

print("Loading speech recognition model...")
_model = WhisperModel("base", device="cpu", compute_type="int8")
print("Ready.")


def listen(duration_seconds: int = 5) -> str:
    """Record from the mic for a fixed duration, return the transcribed text."""
    print(f"Listening for {duration_seconds} seconds...")
    recording = sd.rec(
        int(duration_seconds * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
    )
    sd.wait()

    with wave.open(RECORDING_PATH, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        f.writeframes(recording.tobytes())

    segments, _ = _model.transcribe(RECORDING_PATH)
    return " ".join(segment.text for segment in segments).strip()