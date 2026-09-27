"""Application entry point for the Student Assistant."""

import utils.transport
import utils.session
from dotenv import load_dotenv

from agent import StudentAssistantAgent


def main() -> None:
    """Start the starter Student Assistant application."""
    load_dotenv()
    agent = StudentAssistantAgent()

    print(agent.start())


if __name__ == "__main__":
    main()
