"""
Entry point. Run with: python -m src.main

Push-to-talk: press Enter to start speaking, or type a message
directly instead. Type 'exit' to quit.
"""

from src.assistant import Assistant
from src.voice import listen


def main():
    print("Jarvis (Phase 2 - voice input). Press Enter to talk, or type. Type 'exit' to quit.\n")
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


if __name__ == "__main__":
    main()