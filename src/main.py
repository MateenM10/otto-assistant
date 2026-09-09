import queue

from src.assistant import Assistant
from src.speech import speak
from src.voice import listen
from src.hud_server import (
    start_hud_server,
    set_status,
    set_recording,
    add_message,
    get_next_input,
    mic_start_requested,
)


def main():
    url = start_hud_server()
    print("Jarvis running.")
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

        # Check for a mic press first, then fall back to typed input.
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
                continue  # nothing yet; loop so Ctrl+C stays responsive
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
        add_message("jarvis", reply)
        print(f"Jarvis: {reply}\n")

        set_status("speaking")
        speak(reply)
        set_status("standby")


if __name__ == "__main__":
    main()