"""
High-level chatbot service coordinating RAG and knowledge base ingestion.

Provides the main business logic interface used by API routes and Slack bot.
"""

import time
from typing import Any

from claims_denial_chatbot.config import get_application_settings
from claims_denial_chatbot.core.logging import get_logger
from claims_denial_chatbot.data import SnowflakeKnowledgeBaseConnector
from claims_denial_chatbot.embeddings import TextEmbeddingService
from claims_denial_chatbot.models.schemas import (
    ChatQueryRequest,
    ChatQueryResponse,
    DenialScenario,
    HealthCheckResponse,
    IngestionRequest,
    IngestionResponse,
)
from claims_denial_chatbot.rag import (
    ClaimsDenialRAGChain,
    DenialScenarioDocumentProcessor,
)
from claims_denial_chatbot.vector_store import PineconeVectorStoreManager

logger = get_logger(__name__)


class ClaimsDenialChatbotService:
    """
    Primary service layer for the Claims Denial FAQ Chatbot.

    Encapsulates RAG query execution, health checks, and knowledge base
    ingestion workflows. Injected into FastAPI routes and Slack handlers.
    """

    def __init__(self) -> None:
        """Initialize service with RAG chain and data layer dependencies."""
        self._rag_chain = ClaimsDenialRAGChain()
        self._snowflake_connector = SnowflakeKnowledgeBaseConnector()
        self._embedding_service = TextEmbeddingService()
        self._vector_store = PineconeVectorStoreManager()
        self._document_processor = DenialScenarioDocumentProcessor()
        self._settings = get_application_settings()

    def process_chat_query(self, request: ChatQueryRequest) -> ChatQueryResponse:
        """
        Process a user chat query through the RAG pipeline.

        Args:
            request: Validated ChatQueryRequest with query and optional filters.

        Returns:
            ChatQueryResponse: Generated answer with sources and metadata.
        """
        logger.info(
            "chat_query_received",
            query_length=len(request.query_text),
            denial_code=request.denial_code,
        )
        return self._rag_chain.execute_rag_query(request)

    def perform_health_check(self) -> HealthCheckResponse:
        """
        Check health status of all integrated services.

        Verifies Pinecone index connectivity and reports service statuses.
        Snowflake and Claude are reported as configured (lazy-checked on use).

        Returns:
            HealthCheckResponse: Aggregated health status for all services.
        """
        services: dict[str, str] = {}

        try:
            stats = self._vector_store.get_index_stats()
            vector_count = stats.get("total_vector_count", 0)
            services["pinecone"] = f"healthy ({vector_count} vectors)"
        except Exception as exc:
            services["pinecone"] = f"unhealthy: {exc}"

        services["claude"] = f"configured ({self._settings.claude_model})"
        services["snowflake"] = f"configured ({self._settings.snowflake_database})"
        services["embeddings"] = f"configured ({self._settings.embedding_model})"

        overall_status = (
            "healthy" if all("unhealthy" not in v for v in services.values()) else "degraded"
        )

        return HealthCheckResponse(
            status=overall_status,
            version="1.0.0",
            services=services,
        )

    def ingest_knowledge_base(self, request: IngestionRequest) -> IngestionResponse:
        """
        Ingest denial scenarios from Snowflake into Pinecone vector store.

        Pipeline:
        1. Fetch scenarios from Snowflake (or skip if source=json)
        2. Chunk scenarios into embeddable documents
        3. Generate embeddings in batches
        4. Upsert vectors to Pinecone (optionally clear index first)

        Args:
            request: IngestionRequest with source and reindex options.

        Returns:
            IngestionResponse: Summary of processed scenarios and chunks.
        """
        start_time = time.perf_counter()

        if request.force_reindex:
            self._vector_store.delete_all_vectors()
            logger.info("index_cleared_for_reindex")

        scenarios = self._fetch_scenarios_for_ingestion(request.source)
        document_chunks = self._document_processor.process_scenarios_batch(scenarios)

        texts = [chunk["text"] for chunk in document_chunks]
        embeddings = self._embedding_service.generate_embeddings_for_batch(
            texts, batch_size=request.batch_size
        )

        vectors: list[tuple[str, list[float], dict[str, Any]]] = []
        for idx, (chunk, embedding) in enumerate(zip(document_chunks, embeddings)):
            scenario_id = chunk["metadata"]["scenario_id"]
            chunk_index = chunk["metadata"]["chunk_index"]
            vector_id = f"{scenario_id}_chunk_{chunk_index}"
            vectors.append((vector_id, embedding, chunk["metadata"]))

        total_upserted = 0
        for batch_start in range(0, len(vectors), request.batch_size):
            batch = vectors[batch_start:batch_start + request.batch_size]
            total_upserted += self._vector_store.upsert_document_vectors(batch)

        duration = time.perf_counter() - start_time

        logger.info(
            "knowledge_base_ingestion_completed",
            scenarios=len(scenarios),
            chunks=total_upserted,
            duration_seconds=duration,
        )

        return IngestionResponse(
            total_scenarios_processed=len(scenarios),
            total_chunks_created=total_upserted,
            index_name=self._settings.pinecone_index_name,
            duration_seconds=round(duration, 2),
            status="completed",
        )

    def _fetch_scenarios_for_ingestion(self, source: str) -> list[DenialScenario]:
        """
        Fetch denial scenarios from the specified data source.

        Args:
            source: Data source identifier ('snowflake' or 'json').

        Returns:
            list[DenialScenario]: Scenarios ready for document processing.
        """
        if source == "snowflake":
            return self._snowflake_connector.fetch_all_denial_scenarios()

        logger.warning("unsupported_ingestion_source", source=source)
        return []
