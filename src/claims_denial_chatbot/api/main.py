"""
FastAPI application entry point for the Claims Denial FAQ Chatbot.

Configures middleware, routes, lifespan events, and OpenAPI documentation.
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from claims_denial_chatbot.api.routes import admin_router, chat_router, health_router
from claims_denial_chatbot.config import get_application_settings
from claims_denial_chatbot.core.logging import configure_structured_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def application_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage FastAPI application startup and shutdown lifecycle.

    Configures structured logging on startup and logs application state
    on shutdown.

    Args:
        app: FastAPI application instance.

    Yields:
        None: Control returns to FastAPI during application runtime.
    """
    configure_structured_logging()
    settings = get_application_settings()
    logger.info(
        "application_started",
        app_name=settings.app_name,
        environment=settings.app_env,
    )
    yield
    logger.info("application_shutdown")


def create_fastapi_application() -> FastAPI:
    """
    Factory function to create and configure the FastAPI application.

    Registers routers, CORS middleware, and OpenAPI metadata.
    Use this factory for testing and production deployment.

    Returns:
        FastAPI: Fully configured application instance.
    """
    settings = get_application_settings()

    app = FastAPI(
        title="Claims Denial FAQ Chatbot API",
        description=(
            "RAG-powered API for resolving healthcare claim denials. "
            "Uses LangChain, Claude, Snowflake, and Pinecone for semantic search "
            "across 200+ denial scenarios."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=application_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat_router)
    app.include_router(health_router)
    app.include_router(admin_router)

    @app.get("/", tags=["Root"])
    async def root_endpoint() -> dict[str, str]:
        """Root endpoint returning API identification."""
        return {
            "service": "Claims Denial FAQ Chatbot API",
            "version": "1.0.0",
            "docs": "/docs",
        }

    return app


app = create_fastapi_application()
