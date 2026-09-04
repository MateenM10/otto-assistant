from src.assistant import Assistant


def main():
    print("Jarvis (Phase 1 - text only). Type 'exit' to quit.\n")
    assistant = Assistant()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye.")
            break

        reply = assistant.send(user_input)
        print(f"\nJarvis: {reply}\n")


if __name__ == "__main__":
    main()