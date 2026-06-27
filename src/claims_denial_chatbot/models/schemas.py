"""
Pydantic data models for API requests, responses, and internal data transfer.

Defines strongly-typed schemas for chat queries, denial scenarios,
retrieval results, and RAG pipeline outputs.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from claims_denial_chatbot.core.constants import DenialCategory, DenialSeverity


class DenialScenario(BaseModel):
    """Represents a single claim denial scenario from the knowledge base."""

    scenario_id: str = Field(..., description="Unique identifier for the denial scenario")
    denial_code: str = Field(..., description="CARC/RARC denial code (e.g., CO-16)")
    denial_category: DenialCategory = Field(..., description="Category of denial")
    payer_name: str = Field(..., description="Insurance payer name")
    denial_description: str = Field(..., description="Human-readable denial reason")
    resolution_steps: list[str] = Field(
        default_factory=list, description="Ordered steps to resolve the denial"
    )
    required_documentation: list[str] = Field(
        default_factory=list, description="Documents needed for resubmission"
    )
    severity: DenialSeverity = Field(default=DenialSeverity.MEDIUM)
    average_resolution_days: int = Field(default=14, ge=0)
    success_rate_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RetrievedDocument(BaseModel):
    """A document chunk retrieved from the vector store during semantic search."""

    document_id: str = Field(..., description="Unique document/chunk identifier")
    content: str = Field(..., description="Text content of the retrieved chunk")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Cosine similarity score")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")
    source: str = Field(default="pinecone", description="Retrieval source identifier")


class ChatQueryRequest(BaseModel):
    """Incoming chat query from API or Slack bot."""

    query_text: str = Field(
        ..., min_length=3, max_length=2000, description="User's question about a denial"
    )
    session_id: str | None = Field(
        default=None, description="Optional session ID for conversation tracking"
    )
    denial_code: str | None = Field(
        default=None, description="Optional specific denial code to scope retrieval"
    )
    payer_name: str | None = Field(
        default=None, description="Optional payer name to filter results"
    )
    include_sources: bool = Field(
        default=True, description="Whether to include source documents in response"
    )


class ChatQueryResponse(BaseModel):
    """Structured response from the RAG chatbot."""

    answer_text: str = Field(..., description="Generated answer from Claude")
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence based on retrieval scores"
    )
    retrieved_documents: list[RetrievedDocument] = Field(
        default_factory=list, description="Source documents used for generation"
    )
    denial_code: str | None = Field(
        default=None, description="Identified denial code if applicable"
    )
    resolution_steps: list[str] = Field(
        default_factory=list, description="Extracted resolution steps"
    )
    session_id: str | None = Field(default=None)
    processing_time_ms: float = Field(default=0.0, ge=0.0)
    model_used: str = Field(default="")


class HealthCheckResponse(BaseModel):
    """API health check response."""

    status: str = Field(default="healthy")
    version: str = Field(default="1.0.0")
    services: dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class IngestionRequest(BaseModel):
    """Request to ingest denial scenarios into vector store."""

    source: str = Field(default="snowflake", description="Data source: snowflake or json")
    force_reindex: bool = Field(
        default=False, description="Whether to delete and rebuild the index"
    )
    batch_size: int = Field(default=100, ge=1, le=1000)


class IngestionResponse(BaseModel):
    """Response from knowledge base ingestion job."""

    total_scenarios_processed: int = Field(default=0)
    total_chunks_created: int = Field(default=0)
    index_name: str = Field(default="")
    duration_seconds: float = Field(default=0.0)
    status: str = Field(default="completed")
