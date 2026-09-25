"""Interactive student assistant with tool output for demonstrations."""

from agent import StudentAssistantAgent


def main():
    agent = StudentAssistantAgent(role="student", debug=True)
    print("Student Assistant — type exit or quit to stop.")
    while True:
        try:
            message = input("You: ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if message.lower().strip() in {"exit", "quit"}:
            break
        print("Assistant:", agent.run(message))


if __name__ == "__main__":
    main()
