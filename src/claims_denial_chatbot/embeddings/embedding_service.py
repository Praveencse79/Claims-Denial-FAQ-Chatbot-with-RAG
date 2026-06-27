"""
Text embedding service using OpenAI embedding models.

Generates vector embeddings for denial scenario text and user queries
to enable semantic similarity search in Pinecone.
"""

from typing import Sequence

from langchain_openai import OpenAIEmbeddings

from claims_denial_chatbot.config import get_application_settings
from claims_denial_chatbot.core.exceptions import EmbeddingGenerationError
from claims_denial_chatbot.core.logging import get_logger

logger = get_logger(__name__)


class TextEmbeddingService:
    """
    Generates text embeddings via OpenAI's embedding API.

    Wraps LangChain OpenAIEmbeddings with retry logic and batch processing
    for efficient ingestion of large denial scenario datasets.
    """

    def __init__(self) -> None:
        """Initialize OpenAI embeddings client with configured model."""
        settings = get_application_settings()
        self._embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            openai_api_key=settings.openai_api_key.get_secret_value(),
            dimensions=settings.embedding_dimension,
        )
        self._model_name = settings.embedding_model

    def generate_embedding_for_text(self, text: str) -> list[float]:
        """
        Generate a single embedding vector for the given text.

        Args:
            text: Input text to embed (query or document chunk).

        Returns:
            list[float]: Embedding vector of configured dimension.

        Raises:
            EmbeddingGenerationError: If API call fails or returns empty.
        """
        if not text or not text.strip():
            raise EmbeddingGenerationError("Cannot embed empty text")

        try:
            embedding = self._embeddings.embed_query(text.strip())
            logger.debug("embedding_generated", text_length=len(text))
            return embedding
        except Exception as exc:
            logger.error("embedding_generation_failed", error=str(exc))
            raise EmbeddingGenerationError(
                f"Failed to generate embedding: {exc}"
            ) from exc

    def generate_embeddings_for_batch(
        self, texts: Sequence[str], batch_size: int = 100
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts in batches.

        Processes texts in configurable batch sizes to respect API rate limits
        during bulk ingestion of denial scenarios.

        Args:
            texts: Sequence of text strings to embed.
            batch_size: Number of texts per API batch request.

        Returns:
            list[list[float]]: Embedding vectors in same order as input texts.

        Raises:
            EmbeddingGenerationError: On batch processing failure.
        """
        if not texts:
            return []

        all_embeddings: list[list[float]] = []

        try:
            for batch_start in range(0, len(texts), batch_size):
                batch = list(texts[batch_start:batch_start + batch_size])
                batch_embeddings = self._embeddings.embed_documents(batch)
                all_embeddings.extend(batch_embeddings)

            logger.info(
                "batch_embeddings_generated",
                total_texts=len(texts),
                total_embeddings=len(all_embeddings),
            )
            return all_embeddings

        except Exception as exc:
            logger.error("batch_embedding_failed", error=str(exc))
            raise EmbeddingGenerationError(
                f"Batch embedding generation failed: {exc}"
            ) from exc

    @property
    def model_name(self) -> str:
        """Return the configured embedding model identifier."""
        return self._model_name
