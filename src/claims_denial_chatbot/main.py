"""
CLI entry points for running the API server and Slack bot.

Usage:
    python -m claims_denial_chatbot.main api
    python -m claims_denial_chatbot.main slack
"""

import sys

import uvicorn

from claims_denial_chatbot.config import get_application_settings


def run_api_server() -> None:
    """Start the FastAPI server with uvicorn."""
    settings = get_application_settings()
    uvicorn.run(
        "claims_denial_chatbot.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=1,
        reload=settings.app_env == "development",
    )


def run_slack_bot_entry() -> None:
    """Start the Slack bot in Socket Mode."""
    from claims_denial_chatbot.bot import run_slack_bot

    run_slack_bot()


def main() -> None:
    """Parse CLI argument and run the selected service."""
    if len(sys.argv) < 2:
        print("Usage: python -m claims_denial_chatbot.main [api|slack]")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "api":
        run_api_server()
    elif command == "slack":
        run_slack_bot_entry()
    else:
        print(f"Unknown command: {command}. Use 'api' or 'slack'.")
        sys.exit(1)


if __name__ == "__main__":
    main()
