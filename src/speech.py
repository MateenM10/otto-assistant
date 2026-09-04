import subprocess


def speak(text: str) -> None:
    """Speak the given text out loud using the system voice."""
    if not text:
        return
    subprocess.run(["say", text])