"""
Custom exception hierarchy for the Claims Denial FAQ Chatbot.

Provides typed, domain-specific exceptions for consistent error handling
across API routes, RAG pipeline, and external service integrations.
"""


class ClaimsDenialChatbotError(Exception):
    """Base exception for all chatbot-related errors."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(ClaimsDenialChatbotError):
    """Raised when application configuration is invalid or missing."""


class SnowflakeConnectionError(ClaimsDenialChatbotError):
    """Raised when Snowflake database connection or query fails."""


class PineconeConnectionError(ClaimsDenialChatbotError):
    """Raised when Pinecone vector store connection or operation fails."""


class EmbeddingGenerationError(ClaimsDenialChatbotError):
    """Raised when text embedding generation fails."""


class RetrievalError(ClaimsDenialChatbotError):
    """Raised when document retrieval from vector store fails."""


class LLMGenerationError(ClaimsDenialChatbotError):
    """Raised when Claude API response generation fails."""


class RAGPipelineError(ClaimsDenialChatbotError):
    """Raised when the end-to-end RAG pipeline encounters an error."""


class SlackBotError(ClaimsDenialChatbotError):
    """Raised when Slack bot message handling fails."""


class RateLimitExceededError(ClaimsDenialChatbotError):
    """Raised when API rate limit threshold is exceeded."""
