"""Tests for the Claims Denial RAG chain."""

from unittest.mock import MagicMock

import pytest

from claims_denial_chatbot.models.schemas import ChatQueryRequest, RetrievedDocument
from claims_denial_chatbot.rag.chain import ClaimsDenialRAGChain


class TestClaimsDenialRAGChain:
    """Test suite for end-to-end RAG pipeline."""

    @pytest.fixture
    def sample_retrieved_doc(self) -> RetrievedDocument:
        """Sample retrieved document for testing."""
        return RetrievedDocument(
            document_id="SCN-0001_chunk_0",
            content="CO-16 denial due to missing claim information",
            similarity_score=0.91,
            metadata={
                "scenario_id": "SCN-0001",
                "denial_code": "CO-16",
                "resolution_steps": [
                    "Review remark codes",
                    "Gather documentation",
                    "Resubmit claim",
                ],
            },
        )

    @pytest.fixture
    def mock_retriever(self, sample_retrieved_doc: RetrievedDocument) -> MagicMock:
        """Mock retriever returning sample document."""
        mock = MagicMock()
        mock.retrieve_relevant_documents.return_value = [sample_retrieved_doc]
        mock.calculate_retrieval_confidence.return_value = 0.91
        return mock

    @pytest.fixture
    def mock_llm_client(self) -> MagicMock:
        """Mock Claude client returning formatted response."""
        mock = MagicMock()
        mock.generate_response.return_value = (
            "**Denial Summary**: CO-16 indicates missing information.\n"
            "**Resolution Steps**: Review and resubmit."
        )
        mock.model_name = "claude-sonnet-4-20250514"
        return mock

    @pytest.fixture
    def rag_chain(
        self, mock_retriever: MagicMock, mock_llm_client: MagicMock
    ) -> ClaimsDenialRAGChain:
        """Create RAG chain with mocked dependencies."""
        return ClaimsDenialRAGChain(
            retriever=mock_retriever,
            llm_client=mock_llm_client,
        )

    def test_execute_rag_query_returns_response(
        self, rag_chain: ClaimsDenialRAGChain
    ) -> None:
        """Verify RAG query produces complete ChatQueryResponse."""
        request = ChatQueryRequest(
            query_text="How do I resolve a CO-16 denial?",
            denial_code="CO-16",
        )
        response = rag_chain.execute_rag_query(request)

        assert "CO-16" in response.answer_text
        assert response.confidence_score == 0.91
        assert response.denial_code == "CO-16"
        assert len(response.resolution_steps) == 3
        assert response.processing_time_ms > 0

    def test_execute_rag_query_no_results_uses_fallback(
        self, mock_llm_client: MagicMock
    ) -> None:
        """Verify fallback response when no documents retrieved."""
        mock_retriever = MagicMock()
        mock_retriever.retrieve_relevant_documents.return_value = []
        mock_retriever.calculate_retrieval_confidence.return_value = 0.0
        mock_llm_client.generate_fallback_response.return_value = "No scenario found."

        chain = ClaimsDenialRAGChain(
            retriever=mock_retriever,
            llm_client=mock_llm_client,
        )
        request = ChatQueryRequest(query_text="Unknown denial XYZ-999")
        response = chain.execute_rag_query(request)

        assert response.answer_text == "No scenario found."
        assert response.confidence_score == 0.1
        mock_llm_client.generate_fallback_response.assert_called_once()
