"""
End-to-end RAG chain orchestrating retrieval and generation.

Implements the full Retrieve-Augment-Generate pipeline:
query → embed → retrieve → prompt → Claude → structured response.
"""

import time
import uuid
from typing import Any

from claims_denial_chatbot.config import get_application_settings
from claims_denial_chatbot.core.exceptions import RAGPipelineError
from claims_denial_chatbot.core.logging import get_logger
from claims_denial_chatbot.llm import ClaudeLLMClient, build_rag_user_prompt
from claims_denial_chatbot.models.schemas import ChatQueryRequest, ChatQueryResponse
from claims_denial_chatbot.rag.retriever import DenialScenarioRetriever

logger = get_logger(__name__)


class ClaimsDenialRAGChain:
    """
    Orchestrates the complete RAG pipeline for claims denial queries.

    Coordinates document retrieval, prompt construction, LLM generation,
    and response structuring into ChatQueryResponse.
    """

    def __init__(
        self,
        retriever: DenialScenarioRetriever | None = None,
        llm_client: ClaudeLLMClient | None = None,
    ) -> None:
        """
        Initialize RAG chain with retriever and LLM client dependencies.

        Args:
            retriever: Optional pre-configured document retriever.
            llm_client: Optional pre-configured Claude client.
        """
        self._retriever = retriever or DenialScenarioRetriever()
        self._llm_client = llm_client or ClaudeLLMClient()
        self._settings = get_application_settings()

    def execute_rag_query(self, request: ChatQueryRequest) -> ChatQueryResponse:
        """
        Execute the full RAG pipeline for a user query.

        Steps:
        1. Retrieve semantically similar denial scenarios from Pinecone
        2. Build context-augmented prompt with retrieved documents
        3. Generate response via Claude API
        4. Extract resolution steps and compute confidence score
        5. Return structured ChatQueryResponse

        Args:
            request: Validated chat query request with query text and filters.

        Returns:
            ChatQueryResponse: Complete response with answer, sources, and metadata.

        Raises:
            RAGPipelineError: If any pipeline stage fails irrecoverably.
        """
        start_time = time.perf_counter()
        session_id = request.session_id or str(uuid.uuid4())

        try:
            retrieved_documents = self._retriever.retrieve_relevant_documents(
                query_text=request.query_text,
                denial_code=request.denial_code,
                payer_name=request.payer_name,
            )

            confidence_score = self._retriever.calculate_retrieval_confidence(
                retrieved_documents
            )

            if retrieved_documents:
                context_dicts = self._convert_documents_to_context_dicts(
                    retrieved_documents
                )
                user_prompt = build_rag_user_prompt(
                    user_query=request.query_text,
                    context_documents=context_dicts,
                    denial_code=request.denial_code,
                    payer_name=request.payer_name,
                )
                answer_text = self._llm_client.generate_response(user_prompt)
            else:
                confidence_score = 0.1
                answer_text = self._llm_client.generate_fallback_response(
                    request.query_text
                )

            resolution_steps = self._extract_resolution_steps_from_documents(
                retrieved_documents
            )
            identified_denial_code = self._extract_primary_denial_code(
                retrieved_documents, request.denial_code
            )

            processing_time_ms = (time.perf_counter() - start_time) * 1000

            response = ChatQueryResponse(
                answer_text=answer_text,
                confidence_score=confidence_score,
                retrieved_documents=retrieved_documents if request.include_sources else [],
                denial_code=identified_denial_code,
                resolution_steps=resolution_steps,
                session_id=session_id,
                processing_time_ms=round(processing_time_ms, 2),
                model_used=self._llm_client.model_name,
            )

            logger.info(
                "rag_query_completed",
                session_id=session_id,
                confidence=confidence_score,
                processing_time_ms=processing_time_ms,
                documents_retrieved=len(retrieved_documents),
            )
            return response

        except Exception as exc:
            logger.error("rag_pipeline_failed", error=str(exc), session_id=session_id)
            raise RAGPipelineError(
                f"RAG pipeline execution failed: {exc}",
                details={"session_id": session_id},
            ) from exc

    def _convert_documents_to_context_dicts(
        self, documents: list[Any]
    ) -> list[dict[str, Any]]:
        """
        Convert RetrievedDocument models to dicts for prompt formatting.

        Args:
            documents: List of RetrievedDocument from retriever.

        Returns:
            list[dict]: Dicts with content, metadata, and similarity_score.
        """
        return [
            {
                "content": doc.content,
                "metadata": doc.metadata,
                "similarity_score": doc.similarity_score,
            }
            for doc in documents
        ]

    def _extract_resolution_steps_from_documents(
        self, documents: list[Any]
    ) -> list[str]:
        """
        Extract resolution steps from the top retrieved document's metadata.

        Args:
            documents: Retrieved documents, uses highest-scored first.

        Returns:
            list[str]: Resolution steps if present, empty list otherwise.
        """
        if not documents:
            return []

        top_metadata = documents[0].metadata
        steps = top_metadata.get("resolution_steps", [])
        return steps if isinstance(steps, list) else []

    def _extract_primary_denial_code(
        self,
        documents: list[Any],
        requested_code: str | None,
    ) -> str | None:
        """
        Determine the primary denial code from request or retrieval.

        Prefers explicitly requested denial_code; falls back to top result.

        Args:
            documents: Retrieved documents.
            requested_code: Denial code from user request if provided.

        Returns:
            str | None: Identified denial code or None.
        """
        if requested_code:
            return requested_code

        if documents:
            return documents[0].metadata.get("denial_code")

        return None
