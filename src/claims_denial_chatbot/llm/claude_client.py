"""
Claude LLM client for response generation in the RAG pipeline.

Wraps LangChain's ChatAnthropic with retry logic, token management,
and structured response handling for claims denial queries.
"""

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from tenacity import retry, stop_after_attempt, wait_exponential

from claims_denial_chatbot.config import get_application_settings
from claims_denial_chatbot.core.exceptions import LLMGenerationError
from claims_denial_chatbot.core.logging import get_logger
from claims_denial_chatbot.llm.prompt_templates import (
    CLAIMS_DENIAL_SYSTEM_PROMPT,
    NO_CONTEXT_FALLBACK_PROMPT,
)

logger = get_logger(__name__)


class ClaudeLLMClient:
    """
    Client for generating responses via Anthropic's Claude API.

    Provides synchronous and async generation methods with automatic
    retry on transient API failures.
    """

    def __init__(self) -> None:
        """Initialize ChatAnthropic with application settings."""
        settings = get_application_settings()
        self._client = ChatAnthropic(
            model=settings.claude_model,
            anthropic_api_key=settings.anthropic_api_key.get_secret_value(),
            max_tokens=settings.claude_max_tokens,
            temperature=settings.claude_temperature,
        )
        self._model_name = settings.claude_model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def generate_response(
        self,
        user_prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """
        Generate a text response from Claude for the given prompts.

        Args:
            user_prompt: The formatted user message with context and query.
            system_prompt: Optional system prompt override (defaults to denial expert).

        Returns:
            str: Generated response text from Claude.

        Raises:
            LLMGenerationError: If API call fails after retries.
        """
        system_content = system_prompt or CLAIMS_DENIAL_SYSTEM_PROMPT
        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=user_prompt),
        ]

        try:
            response = self._client.invoke(messages)
            answer_text = response.content

            if not answer_text:
                raise LLMGenerationError("Claude returned empty response")

            logger.info(
                "claude_response_generated",
                model=self._model_name,
                response_length=len(answer_text),
            )
            return str(answer_text)

        except Exception as exc:
            logger.error("claude_generation_failed", error=str(exc))
            raise LLMGenerationError(
                f"Claude API generation failed: {exc}"
            ) from exc

    def generate_fallback_response(self, user_query: str) -> str:
        """
        Generate a helpful fallback when no retrieval context is available.

        Args:
            user_query: Original user question that had no matching scenarios.

        Returns:
            str: Fallback guidance response from Claude.
        """
        fallback_prompt = NO_CONTEXT_FALLBACK_PROMPT.format(user_query=user_query)
        return self.generate_response(fallback_prompt)

    @property
    def model_name(self) -> str:
        """Return the configured Claude model identifier."""
        return self._model_name
