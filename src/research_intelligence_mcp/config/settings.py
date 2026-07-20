"""Validated application settings."""

from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, HttpUrl, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LogFormat = Literal["console", "json"]
MCPTransport = Literal["stdio"]


class Settings(BaseSettings):
    """Configuration loaded from environment variables and `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        populate_by_name=True,
        extra="ignore",
        frozen=True,
    )

    # Application

    app_name: str = Field(
        default="Research Intelligence MCP",
        validation_alias="APP_NAME",
    )

    app_version: str = Field(
        default="0.1.0",
        validation_alias="APP_VERSION",
    )

    app_environment: Environment = Field(
        default="development",
        validation_alias="APP_ENVIRONMENT",
    )

    # MCP

    mcp_server_name: str = Field(
        default="research-intelligence-mcp",
        validation_alias="MCP_SERVER_NAME",
    )

    mcp_transport: MCPTransport = Field(
        default="stdio",
        validation_alias="MCP_TRANSPORT",
    )

    # Logging

    log_level: LogLevel = Field(
        default="INFO",
        validation_alias="LOG_LEVEL",
    )

    log_format: LogFormat = Field(
        default="console",
        validation_alias="LOG_FORMAT",
    )

    # Shared HTTP infrastructure

    http_connect_timeout_seconds: float = Field(
        default=5.0,
        gt=0,
        le=60,
        validation_alias="HTTP_CONNECT_TIMEOUT_SECONDS",
    )

    http_read_timeout_seconds: float = Field(
        default=20.0,
        gt=0,
        le=180,
        validation_alias="HTTP_READ_TIMEOUT_SECONDS",
    )

    http_write_timeout_seconds: float = Field(
        default=20.0,
        gt=0,
        le=180,
        validation_alias="HTTP_WRITE_TIMEOUT_SECONDS",
    )

    http_pool_timeout_seconds: float = Field(
        default=5.0,
        gt=0,
        le=60,
        validation_alias="HTTP_POOL_TIMEOUT_SECONDS",
    )

    http_max_connections: int = Field(
        default=20,
        ge=1,
        le=200,
        validation_alias="HTTP_MAX_CONNECTIONS",
    )

    http_max_keepalive_connections: int = Field(
        default=10,
        ge=0,
        le=100,
        validation_alias="HTTP_MAX_KEEPALIVE_CONNECTIONS",
    )

    http_keepalive_expiry_seconds: float = Field(
        default=30.0,
        gt=0,
        le=300,
        validation_alias="HTTP_KEEPALIVE_EXPIRY_SECONDS",
    )

    http_user_agent: str = Field(
        default="research-intelligence-mcp/0.1.0",
        min_length=1,
        max_length=200,
        validation_alias="HTTP_USER_AGENT",
    )

    # Semantic Scholar

    semantic_scholar_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="SEMANTIC_SCHOLAR_API_KEY",
    )

    semantic_scholar_graph_base_url: HttpUrl = Field(
        default=HttpUrl("https://api.semanticscholar.org/graph/v1"),
        validation_alias="SEMANTIC_SCHOLAR_GRAPH_BASE_URL",
    )

    semantic_scholar_recommendations_base_url: HttpUrl = Field(
        default=HttpUrl("https://api.semanticscholar.org/recommendations/v1"),
        validation_alias="SEMANTIC_SCHOLAR_RECOMMENDATIONS_BASE_URL",
    )

    semantic_scholar_rate_limit_requests: int = Field(
        default=1,
        ge=1,
        le=100,
        validation_alias="SEMANTIC_SCHOLAR_RATE_LIMIT_REQUESTS",
    )

    semantic_scholar_rate_limit_period_seconds: float = Field(
        default=2.0,
        gt=0,
        le=300,
        validation_alias="SEMANTIC_SCHOLAR_RATE_LIMIT_PERIOD_SECONDS",
    )

    semantic_scholar_max_retry_attempts: int = Field(
        default=3,
        ge=1,
        le=6,
        validation_alias="SEMANTIC_SCHOLAR_MAX_RETRY_ATTEMPTS",
    )

    semantic_scholar_retry_min_seconds: float = Field(
        default=2.0,
        ge=0,
        le=60,
        validation_alias="SEMANTIC_SCHOLAR_RETRY_MIN_SECONDS",
    )

    semantic_scholar_retry_max_seconds: float = Field(
        default=20.0,
        ge=1,
        le=300,
        validation_alias="SEMANTIC_SCHOLAR_RETRY_MAX_SECONDS",
    )

    semantic_scholar_live_tests: bool = Field(
        default=False,
        validation_alias="SEMANTIC_SCHOLAR_LIVE_TESTS",
    )

    # arXiv

    arxiv_base_url: HttpUrl = Field(
        default=HttpUrl("https://export.arxiv.org/api"),
        validation_alias="ARXIV_BASE_URL",
    )

    arxiv_rate_limit_requests: int = Field(
        default=1,
        ge=1,
        le=10,
        validation_alias="ARXIV_RATE_LIMIT_REQUESTS",
    )

    arxiv_rate_limit_period_seconds: float = Field(
        default=3.0,
        ge=3.0,
        le=300,
        validation_alias="ARXIV_RATE_LIMIT_PERIOD_SECONDS",
        description=(
            "arXiv legacy APIs require no more than one request every three seconds."
        ),
    )

    arxiv_max_retry_attempts: int = Field(
        default=3,
        ge=1,
        le=6,
        validation_alias="ARXIV_MAX_RETRY_ATTEMPTS",
    )

    arxiv_retry_min_seconds: float = Field(
        default=3.0,
        ge=0,
        le=60,
        validation_alias="ARXIV_RETRY_MIN_SECONDS",
    )

    arxiv_retry_max_seconds: float = Field(
        default=30.0,
        ge=1,
        le=300,
        validation_alias="ARXIV_RETRY_MAX_SECONDS",
    )

    arxiv_max_results_per_request: int = Field(
        default=50,
        ge=1,
        le=2_000,
        validation_alias="ARXIV_MAX_RESULTS_PER_REQUEST",
    )

    arxiv_live_tests: bool = Field(
        default=False,
        validation_alias="ARXIV_LIVE_TESTS",
    )

    @model_validator(mode="after")
    def validate_http_connection_limits(self) -> Self:
        """Ensure keep-alive capacity does not exceed total capacity."""

        if self.http_max_keepalive_connections > self.http_max_connections:
            raise ValueError(
                "HTTP_MAX_KEEPALIVE_CONNECTIONS cannot exceed HTTP_MAX_CONNECTIONS."
            )

        return self

    @model_validator(mode="after")
    def validate_semantic_scholar_retry_range(self) -> Self:
        """Ensure Semantic Scholar retry delays form a valid range."""

        if (
            self.semantic_scholar_retry_min_seconds
            > self.semantic_scholar_retry_max_seconds
        ):
            raise ValueError(
                "SEMANTIC_SCHOLAR_RETRY_MIN_SECONDS cannot exceed "
                "SEMANTIC_SCHOLAR_RETRY_MAX_SECONDS."
            )

        return self

    @model_validator(mode="after")
    def validate_arxiv_retry_range(self) -> Self:
        """Ensure arXiv retry delays form a valid range."""

        if self.arxiv_retry_min_seconds > self.arxiv_retry_max_seconds:
            raise ValueError(
                "ARXIV_RETRY_MIN_SECONDS cannot exceed ARXIV_RETRY_MAX_SECONDS."
            )

        return self

    @model_validator(mode="after")
    def validate_arxiv_rate_limit(self) -> Self:
        """Enforce arXiv's published legacy API request limit."""

        average_interval = (
            self.arxiv_rate_limit_period_seconds / self.arxiv_rate_limit_requests
        )

        if average_interval < 3.0:
            raise ValueError(
                "arXiv API configuration must allow at least three seconds per request."
            )

        return self

    def semantic_scholar_api_key_value(self) -> str | None:
        """Return the configured API key without exposing it in logs."""

        if self.semantic_scholar_api_key is None:
            return None

        value = self.semantic_scholar_api_key.get_secret_value().strip()

        return value or None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings."""

    return Settings()


def clear_settings_cache() -> None:
    """Clear the cached settings instance."""

    get_settings.cache_clear()
