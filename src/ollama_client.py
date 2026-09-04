import requests

OLLAMA_URL = "http://localhost:11434/v1/chat/completions"

messages = []

print("Chatting with local model. Type 'exit' to quit.\n")

while True:
    user_input = input("You: ").strip()
    if user_input.lower() in ("exit", "quit"):
        print("Goodbye.")
        break
    if not user_input:
        continue

    messages.append({"role": "user", "content": user_input})

    response = requests.post(
        OLLAMA_URL,
        json={"model": "llama3.2:3b", "messages": messages},
    )
    data = response.json()
    reply = data["choices"][0]["message"]["content"]

    print(f"\nJarvis: {reply}\n")

    # Save the assistant's reply too, so next turn it remembers what it said
    messages.append({"role": "assistant", "content": reply})