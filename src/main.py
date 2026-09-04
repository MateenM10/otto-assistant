"""
Entry point. Run with: python -m src.main

Push-to-talk: press Enter to start speaking, press Enter again to
stop. Or type a message directly instead. Jarvis speaks its replies
out loud. Type 'dry run' to toggle dry-run mode. Type 'exit' to quit.
"""

from src.assistant import Assistant
from src.voice import listen
from src.speech import speak


def main():
    print("Jarvis (Phase 3 - permissions). Press Enter to talk, or type. Type 'exit' to quit.\n")
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
            user_input = listen()
            print(f"You said: {user_input}")
        else:
            user_input = typed

        if not user_input:
            continue

        reply = assistant.send(user_input)
        print(f"\nJarvis: {reply}\n")
        speak(reply)


if __name__ == "__main__":
    main()