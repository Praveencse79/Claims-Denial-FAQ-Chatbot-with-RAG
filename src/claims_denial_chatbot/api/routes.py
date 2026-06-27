"""
FastAPI route handlers for the Claims Denial FAQ Chatbot API.

Defines REST endpoints for chat queries, health checks, and ingestion.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from claims_denial_chatbot.core.exceptions import (
    ClaimsDenialChatbotError,
    RAGPipelineError,
    RateLimitExceededError,
)
from claims_denial_chatbot.core.logging import get_logger
from claims_denial_chatbot.models.schemas import (
    ChatQueryRequest,
    ChatQueryResponse,
    HealthCheckResponse,
    IngestionRequest,
    IngestionResponse,
)
from claims_denial_chatbot.services import ClaimsDenialChatbotService

logger = get_logger(__name__)

chat_router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])
health_router = APIRouter(prefix="/api/v1/health", tags=["Health"])
admin_router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


def get_chatbot_service() -> ClaimsDenialChatbotService:
    """
    FastAPI dependency providing the chatbot service singleton.

    Returns:
        ClaimsDenialChatbotService: Service instance for route handlers.
    """
    return ClaimsDenialChatbotService()


@chat_router.post(
    "/query",
    response_model=ChatQueryResponse,
    summary="Submit a claims denial question",
    description="Process a natural language query about claim denials using RAG.",
)
async def submit_chat_query(
    request: ChatQueryRequest,
    service: ClaimsDenialChatbotService = Depends(get_chatbot_service),
) -> ChatQueryResponse:
    """
    Handle incoming chat query and return RAG-generated response.

    Args:
        request: ChatQueryRequest with query text and optional filters.
        service: Injected chatbot service dependency.

    Returns:
        ChatQueryResponse: Answer with confidence, sources, and resolution steps.

    Raises:
        HTTPException 500: On RAG pipeline failure.
        HTTPException 429: On rate limit exceeded.
    """
    try:
        return service.process_chat_query(request)
    except RateLimitExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=exc.message,
        ) from exc
    except RAGPipelineError as exc:
        logger.error("chat_query_failed", error=exc.message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process query: {exc.message}",
        ) from exc
    except ClaimsDenialChatbotError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exc.message,
        ) from exc


@health_router.get(
    "",
    response_model=HealthCheckResponse,
    summary="Health check",
    description="Check connectivity and status of all integrated services.",
)
async def get_health_status(
    service: ClaimsDenialChatbotService = Depends(get_chatbot_service),
) -> HealthCheckResponse:
    """
    Return aggregated health status of Pinecone, Claude, Snowflake, and embeddings.

    Returns:
        HealthCheckResponse: Service statuses and overall health indicator.
    """
    return service.perform_health_check()


@admin_router.post(
    "/ingest",
    response_model=IngestionResponse,
    summary="Ingest knowledge base",
    description="Load denial scenarios from Snowflake into Pinecone vector store.",
)
async def trigger_knowledge_base_ingestion(
    request: IngestionRequest,
    service: ClaimsDenialChatbotService = Depends(get_chatbot_service),
) -> IngestionResponse:
    """
    Trigger knowledge base ingestion from Snowflake to Pinecone.

    Args:
        request: IngestionRequest with source and reindex configuration.
        service: Injected chatbot service dependency.

    Returns:
        IngestionResponse: Processing summary with counts and duration.
    """
    try:
        return service.ingest_knowledge_base(request)
    except ClaimsDenialChatbotError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exc.message,
        ) from exc
