"""
Entry point. Run with: python -m src.main

All interaction now happens in the HUD in your browser — this
terminal only shows startup info and permission prompts (moving
those into the HUD is the next step).

Press Ctrl+C here to quit.
"""

import queue

from src.assistant import Assistant
from src.speech import speak
from src.hud_server import start_hud_server, set_status, add_message, get_next_input


def main():
    url = start_hud_server()
    print("Jarvis running.")
    print(f"Open the HUD at {url}")
    print("Type in the HUD to talk to it. Ctrl+C here to quit.\n")

    assistant = Assistant()

    while True:
        try:
            user_input = get_next_input(timeout=0.5)
        except queue.Empty:
            continue  # nothing sent yet; loop again so Ctrl+C stays responsive
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