"""
Pinecone vector store manager for semantic search over denial scenarios.

Handles index creation, document upsertion, and similarity search
against embedded denial scenario chunks.
"""

from typing import Any

from pinecone import Pinecone, ServerlessSpec

from claims_denial_chatbot.config import get_application_settings
from claims_denial_chatbot.core.exceptions import PineconeConnectionError
from claims_denial_chatbot.core.logging import get_logger
from claims_denial_chatbot.models.schemas import RetrievedDocument

logger = get_logger(__name__)


class PineconeVectorStoreManager:
    """
    Manages Pinecone index lifecycle and vector search operations.

    Provides methods to create indexes, upsert embedded document chunks,
    and perform top-k similarity search for RAG retrieval.
    """

    def __init__(self) -> None:
        """Initialize Pinecone client and connect to configured index."""
        self._settings = get_application_settings()
        self._client = Pinecone(
            api_key=self._settings.pinecone_api_key.get_secret_value()
        )
        self._index_name = self._settings.pinecone_index_name
        self._index = self._get_or_create_index()

    def _get_or_create_index(self) -> Any:
        """
        Retrieve existing Pinecone index or create a new one if absent.

        Creates a serverless index with configured dimension and metric
        when the index does not exist.

        Returns:
            Index: Pinecone index handle for upsert and query operations.

        Raises:
            PineconeConnectionError: If index connection fails.
        """
        try:
            existing_indexes = [idx.name for idx in self._client.list_indexes()]
            if self._index_name not in existing_indexes:
                logger.info(
                    "creating_pinecone_index",
                    index_name=self._index_name,
                    dimension=self._settings.pinecone_dimension,
                )
                self._client.create_index(
                    name=self._index_name,
                    dimension=self._settings.pinecone_dimension,
                    metric=self._settings.pinecone_metric,
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=self._settings.pinecone_environment.split("-")[0]
                        + "-" + self._settings.pinecone_environment.split("-")[1],
                    ),
                )
            return self._client.Index(self._index_name)
        except Exception as exc:
            logger.error("pinecone_index_connection_failed", error=str(exc))
            raise PineconeConnectionError(
                f"Failed to connect to Pinecone index: {exc}"
            ) from exc

    def upsert_document_vectors(
        self,
        vectors: list[tuple[str, list[float], dict[str, Any]]],
        namespace: str = "denial_scenarios",
    ) -> int:
        """
        Upsert embedded document vectors into the Pinecone index.

        Args:
            vectors: List of (id, embedding_vector, metadata) tuples.
            namespace: Pinecone namespace for logical partitioning.

        Returns:
            int: Number of vectors successfully upserted.

        Raises:
            PineconeConnectionError: On upsert failure.
        """
        try:
            self._index.upsert(vectors=vectors, namespace=namespace)
            logger.info(
                "vectors_upserted",
                count=len(vectors),
                namespace=namespace,
            )
            return len(vectors)
        except Exception as exc:
            logger.error("vector_upsert_failed", error=str(exc))
            raise PineconeConnectionError(f"Vector upsert failed: {exc}") from exc

    def search_similar_documents(
        self,
        query_embedding: list[float],
        top_k: int | None = None,
        metadata_filter: dict[str, Any] | None = None,
        namespace: str = "denial_scenarios",
    ) -> list[RetrievedDocument]:
        """
        Perform semantic similarity search against the vector index.

        Args:
            query_embedding: Embedding vector of the user's query text.
            top_k: Maximum number of results to return (defaults to RAG_TOP_K_RESULTS).
            metadata_filter: Optional Pinecone metadata filter dict.
            namespace: Namespace to search within.

        Returns:
            list[RetrievedDocument]: Ranked retrieval results with scores and metadata.

        Raises:
            PineconeConnectionError: On search query failure.
        """
        top_k = top_k or self._settings.rag_top_k_results

        try:
            response = self._index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=metadata_filter,
                namespace=namespace,
            )

            retrieved_documents: list[RetrievedDocument] = []
            for match in response.matches:
                if match.score < self._settings.rag_similarity_threshold:
                    continue

                metadata = match.metadata or {}
                content = metadata.get("text", metadata.get("content", ""))

                retrieved_documents.append(
                    RetrievedDocument(
                        document_id=match.id,
                        content=content,
                        similarity_score=match.score,
                        metadata=metadata,
                        source="pinecone",
                    )
                )

            logger.info(
                "similarity_search_completed",
                results_count=len(retrieved_documents),
                top_k=top_k,
            )
            return retrieved_documents

        except Exception as exc:
            logger.error("similarity_search_failed", error=str(exc))
            raise PineconeConnectionError(f"Similarity search failed: {exc}") from exc

    def delete_all_vectors(self, namespace: str = "denial_scenarios") -> None:
        """
        Delete all vectors in a namespace (used during full reindex).

        Args:
            namespace: Namespace to clear before re-ingestion.
        """
        try:
            self._index.delete(delete_all=True, namespace=namespace)
            logger.info("namespace_vectors_deleted", namespace=namespace)
        except Exception as exc:
            logger.error("vector_deletion_failed", error=str(exc))
            raise PineconeConnectionError(f"Vector deletion failed: {exc}") from exc

    def get_index_stats(self) -> dict[str, Any]:
        """
        Retrieve current index statistics (vector count, dimension).

        Returns:
            dict: Index stats from Pinecone describe_index_stats().
        """
        try:
            stats = self._index.describe_index_stats()
            return {
                "total_vector_count": stats.total_vector_count,
                "namespaces": dict(stats.namespaces or {}),
            }
        except Exception as exc:
            raise PineconeConnectionError(f"Failed to get index stats: {exc}") from exc
