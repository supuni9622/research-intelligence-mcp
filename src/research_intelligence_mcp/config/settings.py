"""Validated application settings."""

from functools import lru_cache
from typing import Literal, Self

from pydantic import (
    Field,
    HttpUrl,
    SecretStr,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LogFormat = Literal["console", "json"]
MCPTransport = Literal["stdio", "streamable-http"]

# JWT algorithms this server is willing to trust. HS256 requires a shared
# secret; the asymmetric algorithms require a JWKS endpoint.
JWTAlgorithm = Literal["HS256", "RS256", "ES256", "PS256"]

_ASYMMETRIC_JWT_ALGORITHMS: frozenset[str] = frozenset({"RS256", "ES256", "PS256"})


def _split_comma_separated(value: str) -> list[str]:
    """Split a comma-separated env value into a stripped, non-empty list.

    Kept as a plain `str` field rather than `list[str]`: pydantic-settings
    treats `list[str]` env values as JSON by default, which would reject a
    bare comma-separated value like `RS256,ES256` before any validator runs.
    """

    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    """Configuration loaded from environment variables and `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
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

    mcp_host: str = Field(
        default="127.0.0.1",
        min_length=1,
        max_length=255,
        validation_alias="MCP_HOST",
        description="Bind host used only by the streamable-http transport.",
    )

    mcp_port: int = Field(
        default=8000,
        ge=1,
        le=65_535,
        validation_alias="MCP_PORT",
        description="Bind port used only by the streamable-http transport.",
    )

    # Authentication
    #
    # Stage 1 (local stdio) requires no authentication and these settings are
    # unused. Stage 2 (ResearchMind / service-to-service integration over the
    # streamable-http transport) verifies a bearer JWT issued by a trusted
    # auth server. See docs/research_intelligence_mcp_authentication.md.

    auth_enabled: bool = Field(
        default=False,
        validation_alias="AUTH_ENABLED",
        description=(
            "Require and verify a bearer JWT for streamable-http requests. "
            "Has no effect on the stdio transport."
        ),
    )

    auth_issuer: str | None = Field(
        default=None,
        min_length=1,
        max_length=2_048,
        validation_alias="AUTH_ISSUER",
        description=(
            "Expected `iss` claim, e.g. https://auth.researchmind.ai. Stored "
            "and compared verbatim (unlike an `HttpUrl` field, this is not "
            "silently normalized with a trailing slash), because issuer "
            "matching against a token's `iss` claim must be an exact string "
            "match."
        ),
    )

    auth_audience: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        validation_alias="AUTH_AUDIENCE",
        description="Expected `aud` claim, e.g. research-intelligence-mcp",
    )

    auth_resource_server_url: HttpUrl | None = Field(
        default=None,
        validation_alias="AUTH_RESOURCE_SERVER_URL",
        description=(
            "Public URL of this MCP server, used for OAuth protected resource metadata."
        ),
    )

    auth_jwks_url: HttpUrl | None = Field(
        default=None,
        validation_alias="AUTH_JWKS_URL",
        description="JWKS endpoint used to verify RS256/ES256/PS256 tokens.",
    )

    auth_jwt_secret: SecretStr | None = Field(
        default=None,
        validation_alias="AUTH_JWT_SECRET",
        description=(
            "Shared secret used to verify HS256 tokens. Intended for local "
            "and test environments only; production deployments should use "
            "AUTH_JWKS_URL with an asymmetric algorithm."
        ),
    )

    auth_jwt_algorithms: str = Field(
        default="RS256",
        min_length=1,
        validation_alias="AUTH_JWT_ALGORITHMS",
        description="Accepted JWT signing algorithms, comma-separated.",
    )

    auth_required_scopes: str = Field(
        default="research-intelligence/invoke",
        min_length=1,
        validation_alias="AUTH_REQUIRED_SCOPES",
        description="Scopes a token must carry, comma-separated.",
    )

    auth_jwt_leeway_seconds: float = Field(
        default=30.0,
        ge=0,
        le=300,
        validation_alias="AUTH_JWT_LEEWAY_SECONDS",
        description="Clock-skew tolerance applied to `exp`/`nbf`/`iat` checks.",
    )

    auth_jwks_cache_ttl_seconds: float = Field(
        default=300.0,
        ge=30,
        le=86_400,
        validation_alias="AUTH_JWKS_CACHE_TTL_SECONDS",
        description="How long fetched JWKS signing keys stay cached.",
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

    # In-memory caching

    cache_enabled: bool = Field(
        default=True,
        validation_alias="CACHE_ENABLED",
    )

    search_cache_max_size: int = Field(
        default=500,
        ge=1,
        le=10_000,
        validation_alias="SEARCH_CACHE_MAX_SIZE",
    )

    search_cache_ttl_seconds: float = Field(
        default=900.0,
        gt=0,
        le=86_400,
        validation_alias="SEARCH_CACHE_TTL_SECONDS",
    )

    paper_cache_max_size: int = Field(
        default=5_000,
        ge=1,
        le=100_000,
        validation_alias="PAPER_CACHE_MAX_SIZE",
    )

    paper_cache_ttl_seconds: float = Field(
        default=86_400.0,
        gt=0,
        le=604_800,
        validation_alias="PAPER_CACHE_TTL_SECONDS",
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

    @model_validator(mode="after")
    def validate_auth_configuration(self) -> Self:
        """Ensure a usable signing-key source exists when auth is enabled."""

        if not self.auth_enabled:
            return self

        if self.auth_issuer is None:
            raise ValueError("AUTH_ISSUER is required when AUTH_ENABLED is true.")

        if not self.auth_audience:
            raise ValueError("AUTH_AUDIENCE is required when AUTH_ENABLED is true.")

        algorithm_list = self.auth_jwt_algorithms_list()

        if not algorithm_list:
            raise ValueError(
                "AUTH_JWT_ALGORITHMS must list at least one algorithm when "
                "AUTH_ENABLED is true."
            )

        algorithms = set(algorithm_list)
        needs_secret = "HS256" in algorithms
        needs_jwks = bool(algorithms & _ASYMMETRIC_JWT_ALGORITHMS)

        if needs_secret and self.auth_jwt_secret_value() is None:
            raise ValueError(
                "AUTH_JWT_SECRET is required when AUTH_JWT_ALGORITHMS includes HS256."
            )

        if needs_jwks and self.auth_jwks_url is None:
            raise ValueError(
                "AUTH_JWKS_URL is required when AUTH_JWT_ALGORITHMS includes an "
                "asymmetric algorithm (RS256, ES256, or PS256)."
            )

        return self

    def semantic_scholar_api_key_value(self) -> str | None:
        """Return the configured API key without exposing it in logs."""

        if self.semantic_scholar_api_key is None:
            return None

        value = self.semantic_scholar_api_key.get_secret_value().strip()

        return value or None

    def auth_jwt_secret_value(self) -> str | None:
        """Return the configured JWT shared secret without exposing it in logs."""

        if self.auth_jwt_secret is None:
            return None

        value = self.auth_jwt_secret.get_secret_value().strip()

        return value or None

    def auth_jwt_algorithms_list(self) -> list[str]:
        """Return the configured JWT algorithms as a list."""

        return _split_comma_separated(self.auth_jwt_algorithms)

    def auth_required_scopes_list(self) -> list[str]:
        """Return the configured required scopes as a list."""

        return _split_comma_separated(self.auth_required_scopes)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings."""

    return Settings()


def clear_settings_cache() -> None:
    """Clear the cached settings instance."""

    get_settings.cache_clear()
