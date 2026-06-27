"""Tests for the Claims Denial RAG retriever."""

from unittest.mock import MagicMock, patch

import pytest

from claims_denial_chatbot.models.schemas import RetrievedDocument
from claims_denial_chatbot.rag.retriever import DenialScenarioRetriever


class TestDenialScenarioRetriever:
    """Test suite for DenialScenarioRetriever semantic search."""

    @pytest.fixture
    def mock_embedding_service(self) -> MagicMock:
        """Create mock embedding service returning fixed vector."""
        mock = MagicMock()
        mock.generate_embedding_for_text.return_value = [0.1] * 1536
        return mock

    @pytest.fixture
    def mock_vector_store(self) -> MagicMock:
        """Create mock vector store returning sample documents."""
        mock = MagicMock()
        mock.search_similar_documents.return_value = [
            RetrievedDocument(
                document_id="SCN-0001_chunk_0",
                content="CO-16 denial: missing information on claim",
                similarity_score=0.92,
                metadata={
                    "scenario_id": "SCN-0001",
                    "denial_code": "CO-16",
                    "denial_category": "coding",
                    "payer_name": "Medicare",
                    "resolution_steps": ["Review claim", "Correct errors", "Resubmit"],
                },
            )
        ]
        return mock

    @pytest.fixture
    def retriever(
        self, mock_embedding_service: MagicMock, mock_vector_store: MagicMock
    ) -> DenialScenarioRetriever:
        """Create retriever with mocked dependencies."""
        return DenialScenarioRetriever(
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
        )

    def test_retrieve_relevant_documents_returns_results(
        self, retriever: DenialScenarioRetriever
    ) -> None:
        """Verify retrieval returns documents with expected structure."""
        results = retriever.retrieve_relevant_documents(
            query_text="How do I fix CO-16 denial?"
        )
        assert len(results) == 1
        assert results[0].similarity_score == 0.92
        assert results[0].metadata["denial_code"] == "CO-16"

    def test_retrieve_with_denial_code_filter(
        self,
        retriever: DenialScenarioRetriever,
        mock_vector_store: MagicMock,
    ) -> None:
        """Verify denial code filter is passed to vector store."""
        retriever.retrieve_relevant_documents(
            query_text="missing information denial",
            denial_code="CO-16",
        )
        call_kwargs = mock_vector_store.search_similar_documents.call_args
        assert call_kwargs.kwargs["metadata_filter"] == {"denial_code": {"$eq": "CO-16"}}

    def test_calculate_confidence_with_documents(
        self, retriever: DenialScenarioRetriever
    ) -> None:
        """Verify confidence calculation from similarity scores."""
        docs = [
            RetrievedDocument(
                document_id="1", content="a", similarity_score=0.9, metadata={}
            ),
            RetrievedDocument(
                document_id="2", content="b", similarity_score=0.8, metadata={}
            ),
        ]
        confidence = retriever.calculate_retrieval_confidence(docs)
        assert confidence == 0.85

    def test_calculate_confidence_empty_returns_zero(
        self, retriever: DenialScenarioRetriever
    ) -> None:
        """Verify zero confidence when no documents retrieved."""
        assert retriever.calculate_retrieval_confidence([]) == 0.0
