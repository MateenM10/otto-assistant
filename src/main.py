import queue
import threading

from src.assistant import Assistant
from src.speech import speak
from src.voice import listen
from src.memory import extract_facts
from src.hud_server import (
    start_hud_server,
    set_status,
    set_recording,
    set_streaming,
    add_message,
    add_event,
    get_next_input,
    mic_start_requested,
    speech_enabled,
)


def _extract_in_background(assistant, user_input: str, reply: str) -> None:
    """Run memory extraction off the main thread. Failures are silent —
    memory is a nice-to-have, never a reason to interrupt the user."""
    try:
        new_facts = extract_facts(assistant.backend, user_input, reply)
        for fact in new_facts:
            print(f"[memory] learned: {fact}")
            add_event("remember", {"fact": fact}, "allowed")
    except Exception:
        pass


def main():
    url = start_hud_server()
    print("Otto running.")
    print(f"Open the HUD at {url}")

    try:
        assistant = Assistant()
    except RuntimeError as e:
        print(f"\nCouldn't start: {e}")
        return

    print(f"Backend: {assistant.backend.__class__.__name__} ({assistant.backend.model})")
    print("Type or press the mic button in the HUD. Ctrl+C here to quit.\n")

    while True:
        user_input = None

        if mic_start_requested():
            set_status("listening")
            set_recording(True)
            user_input = listen()
            set_recording(False)
            if not user_input:
                set_status("standby")
                continue
        else:
            try:
                user_input = get_next_input(timeout=0.2)
            except queue.Empty:
                continue
            except KeyboardInterrupt:
                print("\nGoodbye.")
                break

        if user_input.lower() in ("exit", "quit"):
            add_message("system", "Session ended.")
            print("Goodbye.")
            break

        if user_input.lower() == "dry run":
            message = assistant.toggle_dry_run()
            add_message("system", message)
            print(message)
            continue

        add_message("user", user_input)
        print(f"You: {user_input}")

        reply = assistant.send(user_input)

        # Add the finished reply, then clear the live streaming text —
        # this order avoids a flicker where neither is on screen.
        add_message("otto", reply)
        set_streaming("")
        print(f"Otto: {reply}\n")

        threading.Thread(
            target=_extract_in_background,
            args=(assistant, user_input, reply),
            daemon=True,
        ).start()

        if speech_enabled():
            set_status("speaking")
            speak(reply)
        set_status("standby")


if __name__ == "__main__":
    main()