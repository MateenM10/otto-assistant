"""
Entry point. Run with: python -m src.main

Push-to-talk: press Enter to start speaking, press Enter again to
stop. Or type a message directly instead. Jarvis speaks its replies
out loud. Type 'dry run' to toggle dry-run mode. Type 'exit' to quit.

Also starts the HUD server, which serves a visual status display at
http://localhost:8765/index.html showing what the assistant is doing.
"""

from src.assistant import Assistant
from src.voice import listen
from src.speech import speak
from src.hud_server import start_hud_server, set_status


def main():
    print("Jarvis (Phase 4 - HUD). Press Enter to talk, or type. Type 'exit' to quit.\n")

    url = start_hud_server()
    print(f"HUD available at {url}\n")

    assistant = Assistant()

    while True:
        try:
            typed = input("You (press Enter to talk instead): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if typed.lower() in ("exit", "quit"):
            print("Goodbye.")
            break

        if typed.lower() == "dry run":
            print(assistant.toggle_dry_run())
            continue

        if typed == "":
            # Empty input means they just pressed Enter -> start listening
            set_status("listening")
            user_input = listen()
            print(f"You said: {user_input}")
        else:
            user_input = typed

        if not user_input:
            set_status("standby")
            continue

        reply = assistant.send(user_input)
        print(f"\nJarvis: {reply}\n")

        set_status("speaking")
        speak(reply)
        set_status("standby")


if __name__ == "__main__":
    main()