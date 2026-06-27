"""
Slack bot integration for the Claims Denial FAQ Chatbot.

Handles slash commands, direct messages, and app mentions using
Slack Bolt framework with Socket Mode for real-time event delivery.
"""

import re

from typing import Callable

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from claims_denial_chatbot.config import get_application_settings
from claims_denial_chatbot.core.constants import SLACK_COMMAND_PREFIX, SLACK_HELP_COMMAND
from claims_denial_chatbot.core.logging import configure_structured_logging, get_logger
from claims_denial_chatbot.models.schemas import ChatQueryRequest
from claims_denial_chatbot.services import ClaimsDenialChatbotService

logger = get_logger(__name__)


class ClaimsDenialSlackBot:
    """
    Slack bot wrapper for the Claims Denial FAQ Chatbot.

    Registers event handlers for slash commands, mentions, and direct messages.
    Formats RAG responses for Slack's markdown-compatible message format.
    """

    def __init__(self) -> None:
        """Initialize Slack Bolt app and register event handlers."""
        settings = get_application_settings()
        self._chatbot_service = ClaimsDenialChatbotService()
        self._app = App(
            token=settings.slack_bot_token.get_secret_value(),
            signing_secret=settings.slack_signing_secret.get_secret_value(),
        )
        self._app_token = settings.slack_app_token.get_secret_value()
        self._register_event_handlers()

    def _register_event_handlers(self) -> None:
        """Register all Slack event and command handlers on the Bolt app."""
        self._app.command(SLACK_COMMAND_PREFIX)(self._handle_denial_command)
        self._app.command(SLACK_HELP_COMMAND)(self._handle_help_command)
        self._app.event("app_mention")(self._handle_app_mention)
        self._app.event("message")(self._handle_direct_message)

    def _handle_denial_command(
        self, ack: Callable, command: dict, say: Callable
    ) -> None:
        """
        Handle /denial slash command for structured denial queries.

        Parses optional --code and --payer flags from command text.

        Args:
            ack: Slack acknowledgment function (must be called first).
            command: Slash command payload from Slack.
            say: Function to send a message to the channel.
        """
        ack()
        query_text = command.get("text", "").strip()

        if not query_text:
            say("Please provide a question. Example: `/denial How do I resolve CO-16 denial?`")
            return

        denial_code = self._extract_flag_value(query_text, "--code")
        payer_name = self._extract_flag_value(query_text, "--payer")
        clean_query = self._remove_flags_from_query(query_text)

        self._process_and_respond(
            say=say,
            query_text=clean_query,
            denial_code=denial_code,
            payer_name=payer_name,
            thread_ts=command.get("ts"),
        )

    def _handle_help_command(self, ack: Callable, say: Callable) -> None:
        """
        Handle /denial-help slash command with usage instructions.

        Args:
            ack: Slack acknowledgment function.
            say: Function to send help message.
        """
        ack()
        help_text = (
            "*Claims Denial FAQ Chatbot Help*\n\n"
            "*Commands:*\n"
            "• `/denial <question>` — Ask about a claim denial\n"
            "• `/denial --code CO-16 <question>` — Query with denial code filter\n"
            "• `/denial --payer Medicare <question>` — Query with payer filter\n"
            "• `/denial-help` — Show this help message\n\n"
            "*Examples:*\n"
            "• `/denial How do I resolve a timely filing denial?`\n"
            "• `/denial --code CO-197 What authorization is needed?`\n"
            "• Mention me in a channel with your denial question"
        )
        say(help_text)

    def _handle_app_mention(self, event: dict, say: Callable) -> None:
        """
        Handle @bot mentions in channels.

        Args:
            event: Slack event payload for app_mention.
            say: Function to reply in the thread.
        """
        text = event.get("text", "")
        clean_query = re.sub(r"<@[A-Z0-9]+>", "", text).strip()

        if not clean_query:
            say("Hi! Ask me about claim denials. Example: '@bot How do I fix CO-16?'", thread_ts=event.get("ts"))
            return

        self._process_and_respond(
            say=say,
            query_text=clean_query,
            thread_ts=event.get("ts"),
        )

    def _handle_direct_message(self, event: dict, say: Callable) -> None:
        """
        Handle direct messages sent to the bot.

        Skips bot messages and subtype events to avoid loops.

        Args:
            event: Slack message event payload.
            say: Function to send DM response.
        """
        if event.get("subtype") or event.get("bot_id"):
            return

        channel_type = event.get("channel_type", "")
        if channel_type != "im":
            return

        query_text = event.get("text", "").strip()
        if not query_text:
            return

        self._process_and_respond(say=say, query_text=query_text)

    def _process_and_respond(
        self,
        say: Callable,
        query_text: str,
        denial_code: str | None = None,
        payer_name: str | None = None,
        thread_ts: str | None = None,
    ) -> None:
        """
        Execute RAG query and format response for Slack.

        Args:
            say: Slack say function for sending messages.
            query_text: User's question text.
            denial_code: Optional denial code filter.
            payer_name: Optional payer filter.
            thread_ts: Optional thread timestamp for threaded replies.
        """
        try:
            say("Searching knowledge base...", thread_ts=thread_ts)

            request = ChatQueryRequest(
                query_text=query_text,
                denial_code=denial_code,
                payer_name=payer_name,
                include_sources=True,
            )
            response = self._chatbot_service.process_chat_query(request)

            formatted_message = self._format_response_for_slack(response)
            say(formatted_message, thread_ts=thread_ts)

        except Exception as exc:
            logger.error("slack_query_failed", error=str(exc))
            say(
                f"Sorry, I encountered an error processing your question. "
                f"Please try again or contact support. Error: {exc}",
                thread_ts=thread_ts,
            )

    def _format_response_for_slack(self, response: object) -> str:
        """
        Format ChatQueryResponse into Slack-compatible markdown message.

        Args:
            response: ChatQueryResponse from chatbot service.

        Returns:
            str: Formatted message string for Slack.
        """
        parts = [response.answer_text]

        if response.denial_code:
            parts.append(f"\n*Identified Denial Code:* `{response.denial_code}`")

        if response.resolution_steps:
            steps = "\n".join(f"  {i+1}. {step}" for i, step in enumerate(response.resolution_steps))
            parts.append(f"\n*Quick Resolution Steps:*\n{steps}")

        parts.append(
            f"\n_Confidence: {response.confidence_score:.0%} | "
            f"Processed in {response.processing_time_ms:.0f}ms_"
        )

        if response.retrieved_documents:
            sources = ", ".join(
                doc.metadata.get("denial_code", doc.document_id)
                for doc in response.retrieved_documents[:3]
            )
            parts.append(f"\n*Sources:* {sources}")

        return "\n".join(parts)

    def _extract_flag_value(self, text: str, flag: str) -> str | None:
        """
        Extract value following a CLI-style flag from command text.

        Args:
            text: Full command text string.
            flag: Flag name (e.g., '--code').

        Returns:
            str | None: Flag value if present, None otherwise.
        """
        pattern = rf"{flag}\s+(\S+)"
        match = re.search(pattern, text)
        return match.group(1) if match else None

    def _remove_flags_from_query(self, text: str) -> str:
        """
        Remove --code and --payer flags and their values from query text.

        Args:
            text: Raw command text with possible flags.

        Returns:
            str: Clean query text without flags.
        """
        cleaned = re.sub(r"--code\s+\S+", "", text)
        cleaned = re.sub(r"--payer\s+\S+", "", cleaned)
        return cleaned.strip()

    def start(self) -> None:
        """
        Start the Slack bot using Socket Mode.

        Blocks until the bot is stopped. Call from main entry point
        or deployment script.
        """
        configure_structured_logging()
        logger.info("slack_bot_starting")
        handler = SocketModeHandler(self._app, self._app_token)
        handler.start()


def run_slack_bot() -> None:
    """Entry point function to start the Slack bot."""
    bot = ClaimsDenialSlackBot()
    bot.start()
