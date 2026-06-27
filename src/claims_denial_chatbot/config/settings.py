"""
Claims Denial FAQ Chatbot - Application Configuration.

Centralizes all environment-driven settings using Pydantic Settings.
All configuration values are loaded from environment variables or .env file.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApplicationSettings(BaseSettings):
    """Top-level application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="claims-denial-faq-chatbot", alias="APP_NAME")
    app_env: Literal["development", "staging", "production"] = Field(
        default="development", alias="APP_ENV"
    )
    app_debug: bool = Field(default=False, alias="APP_DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # FastAPI Server
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_workers: int = Field(default=4, alias="API_WORKERS")

    # Anthropic Claude API
    anthropic_api_key: SecretStr = Field(alias="ANTHROPIC_API_KEY")
    claude_model: str = Field(default="claude-sonnet-4-20250514", alias="CLAUDE_MODEL")
    claude_max_tokens: int = Field(default=1024, alias="CLAUDE_MAX_TOKENS")
    claude_temperature: float = Field(default=0.1, alias="CLAUDE_TEMPERATURE")

    # Pinecone Vector Database
    pinecone_api_key: SecretStr = Field(alias="PINECONE_API_KEY")
    pinecone_environment: str = Field(default="us-east-1-aws", alias="PINECONE_ENVIRONMENT")
    pinecone_index_name: str = Field(default="claims-denial-faq", alias="PINECONE_INDEX_NAME")
    pinecone_dimension: int = Field(default=1536, alias="PINECONE_DIMENSION")
    pinecone_metric: str = Field(default="cosine", alias="PINECONE_METRIC")

    # Embedding Model
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    embedding_dimension: int = Field(default=1536, alias="EMBEDDING_DIMENSION")
    openai_api_key: SecretStr = Field(alias="OPENAI_API_KEY")

    # Snowflake Knowledge Base
    snowflake_account: str = Field(alias="SNOWFLAKE_ACCOUNT")
    snowflake_user: str = Field(alias="SNOWFLAKE_USER")
    snowflake_password: SecretStr = Field(alias="SNOWFLAKE_PASSWORD")
    snowflake_warehouse: str = Field(default="COMPUTE_WH", alias="SNOWFLAKE_WAREHOUSE")
    snowflake_database: str = Field(default="CLAIMS_DB", alias="SNOWFLAKE_DATABASE")
    snowflake_schema: str = Field(default="DENIAL_KB", alias="SNOWFLAKE_SCHEMA")
    snowflake_role: str = Field(default="ANALYST_ROLE", alias="SNOWFLAKE_ROLE")
    snowflake_denial_table: str = Field(default="DENIAL_SCENARIOS", alias="SNOWFLAKE_DENIAL_TABLE")

    # RAG Configuration
    rag_top_k_results: int = Field(default=5, alias="RAG_TOP_K_RESULTS")
    rag_similarity_threshold: float = Field(default=0.75, alias="RAG_SIMILARITY_THRESHOLD")
    rag_chunk_size: int = Field(default=512, alias="RAG_CHUNK_SIZE")
    rag_chunk_overlap: int = Field(default=64, alias="RAG_CHUNK_OVERLAP")
    rag_max_context_tokens: int = Field(default=4000, alias="RAG_MAX_CONTEXT_TOKENS")

    # Slack Bot
    slack_bot_token: SecretStr = Field(alias="SLACK_BOT_TOKEN")
    slack_app_token: SecretStr = Field(alias="SLACK_APP_TOKEN")
    slack_signing_secret: SecretStr = Field(alias="SLACK_SIGNING_SECRET")

    # Rate Limiting
    rate_limit_requests: int = Field(default=60, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS")


@lru_cache
def get_application_settings() -> ApplicationSettings:
    """
    Retrieve cached application settings singleton.

    Uses LRU cache to ensure settings are loaded once per process lifecycle.
    Call this function instead of instantiating ApplicationSettings directly.

    Returns:
        ApplicationSettings: Validated configuration object with all env vars loaded.
    """
    return ApplicationSettings()
