"""Tests for FastAPI endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from claims_denial_chatbot.api.main import create_fastapi_application
from claims_denial_chatbot.models.schemas import ChatQueryResponse, HealthCheckResponse


@pytest.fixture
def client() -> TestClient:
    """Create test client with fresh FastAPI app."""
    app = create_fastapi_application()
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for /api/v1/health endpoint."""

    @patch("claims_denial_chatbot.api.routes.ClaimsDenialChatbotService")
    def test_health_check_returns_status(
        self, mock_service_class: MagicMock, client: TestClient
    ) -> None:
        """Verify health endpoint returns structured response."""
        mock_service = MagicMock()
        mock_service.perform_health_check.return_value = HealthCheckResponse(
            status="healthy",
            services={"pinecone": "healthy (210 vectors)"},
        )
        mock_service_class.return_value = mock_service

        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestChatEndpoint:
    """Tests for /api/v1/chat/query endpoint."""

    @patch("claims_denial_chatbot.api.routes.ClaimsDenialChatbotService")
    def test_chat_query_success(
        self, mock_service_class: MagicMock, client: TestClient
    ) -> None:
        """Verify chat query endpoint returns RAG response."""
        mock_service = MagicMock()
        mock_service.process_chat_query.return_value = ChatQueryResponse(
            answer_text="Resolve CO-16 by correcting missing information.",
            confidence_score=0.89,
            denial_code="CO-16",
            resolution_steps=["Review claim", "Resubmit"],
            processing_time_ms=450.0,
            model_used="claude-sonnet-4-20250514",
        )
        mock_service_class.return_value = mock_service

        response = client.post(
            "/api/v1/chat/query",
            json={"query_text": "How do I fix CO-16?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["confidence_score"] == 0.89
        assert data["denial_code"] == "CO-16"

    def test_chat_query_validation_error(self, client: TestClient) -> None:
        """Verify validation rejects empty query text."""
        response = client.post(
            "/api/v1/chat/query",
            json={"query_text": "ab"},
        )
        assert response.status_code == 422
