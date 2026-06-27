"""
Semantic retriever for denial scenario documents.

Orchestrates query embedding and Pinecone similarity search with
optional metadata filtering by denial code and payer.
"""

from typing import Any

from claims_denial_chatbot.config import get_application_settings
from claims_denial_chatbot.core.exceptions import RetrievalError
from claims_denial_chatbot.core.logging import get_logger
from claims_denial_chatbot.embeddings import TextEmbeddingService
from claims_denial_chatbot.models.schemas import RetrievedDocument
from claims_denial_chatbot.vector_store import PineconeVectorStoreManager

logger = get_logger(__name__)


class DenialScenarioRetriever:
    """
    Retrieves relevant denial scenario documents via semantic search.

    Embeds user queries and searches Pinecone with configurable
    top-k and metadata filters for scoped retrieval.
    """

    def __init__(
        self,
        embedding_service: TextEmbeddingService | None = None,
        vector_store: PineconeVectorStoreManager | None = None,
    ) -> None:
        """
        Initialize retriever with embedding and vector store dependencies.

        Args:
            embedding_service: Optional pre-configured embedding service.
            vector_store: Optional pre-configured Pinecone manager.
        """
        self._embedding_service = embedding_service or TextEmbeddingService()
        self._vector_store = vector_store or PineconeVectorStoreManager()
        self._settings = get_application_settings()

    def retrieve_relevant_documents(
        self,
        query_text: str,
        denial_code: str | None = None,
        payer_name: str | None = None,
        top_k: int | None = None,
    ) -> list[RetrievedDocument]:
        """
        Retrieve top-k semantically similar denial scenario documents.

        Args:
            query_text: User's natural language query.
            denial_code: Optional filter to scope by CARC/RARC code.
            payer_name: Optional filter to scope by insurance payer.
            top_k: Override default number of results.

        Returns:
            list[RetrievedDocument]: Ranked documents above similarity threshold.

        Raises:
            RetrievalError: If embedding or search fails.
        """
        try:
            query_embedding = self._embedding_service.generate_embedding_for_text(
                query_text
            )
            metadata_filter = self._build_metadata_filter(denial_code, payer_name)

            retrieved = self._vector_store.search_similar_documents(
                query_embedding=query_embedding,
                top_k=top_k,
                metadata_filter=metadata_filter,
            )

            logger.info(
                "documents_retrieved",
                query_length=len(query_text),
                results_count=len(retrieved),
                denial_code=denial_code,
                payer_name=payer_name,
            )
            return retrieved

        except Exception as exc:
            logger.error("document_retrieval_failed", error=str(exc))
            raise RetrievalError(f"Document retrieval failed: {exc}") from exc

    def _build_metadata_filter(
        self,
        denial_code: str | None,
        payer_name: str | None,
    ) -> dict[str, Any] | None:
        """
        Build Pinecone metadata filter from optional query parameters.

        Args:
            denial_code: CARC/RARC code to filter by.
            payer_name: Payer name to filter by.

        Returns:
            dict | None: Pinecone filter dict, or None if no filters applied.
        """
        filters: dict[str, Any] = {}

        if denial_code:
            filters["denial_code"] = {"$eq": denial_code}

        if payer_name:
            filters["payer_name"] = {"$eq": payer_name}

        return filters if filters else None

    def calculate_retrieval_confidence(
        self, retrieved_documents: list[RetrievedDocument]
    ) -> float:
        """
        Compute aggregate confidence score from retrieval similarity scores.

        Uses the mean of top retrieval scores, capped at 1.0.
        Returns 0.0 if no documents were retrieved.

        Args:
            retrieved_documents: Documents returned from similarity search.

        Returns:
            float: Confidence score between 0.0 and 1.0.
        """
        if not retrieved_documents:
            return 0.0

        scores = [doc.similarity_score for doc in retrieved_documents]
        return min(sum(scores) / len(scores), 1.0)
