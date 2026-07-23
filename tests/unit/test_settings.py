"""Tests for application settings."""

import pytest
from pydantic import ValidationError

from research_intelligence_mcp.config.settings import (
    Settings,
    clear_settings_cache,
    get_settings,
)


def test_default_settings() -> None:
    """Settings should provide safe local defaults."""

    settings = Settings(_env_file=None)

    assert settings.app_name == "Research Intelligence MCP"
    assert settings.app_version == "0.1.0"
    assert settings.app_environment == "development"
    assert settings.mcp_server_name == "research-intelligence-mcp"
    assert settings.mcp_transport == "stdio"
    assert settings.log_level == "INFO"
    assert settings.log_format == "console"

    assert settings.http_connect_timeout_seconds == 5
    assert settings.http_read_timeout_seconds == 20
    assert settings.http_max_connections == 20
    assert settings.http_max_keepalive_connections == 10

    assert settings.semantic_scholar_api_key_value() is None
    assert settings.semantic_scholar_rate_limit_requests == 1
    assert settings.semantic_scholar_rate_limit_period_seconds == 2
    assert settings.semantic_scholar_live_tests is False


def test_settings_can_be_loaded_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Environment variables should override defaults."""

    monkeypatch.setenv("APP_ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_FORMAT", "json")
    monkeypatch.setenv("HTTP_MAX_CONNECTIONS", "30")
    monkeypatch.setenv(
        "SEMANTIC_SCHOLAR_RATE_LIMIT_PERIOD_SECONDS",
        "5",
    )

    settings = Settings(_env_file=None)

    assert settings.app_environment == "test"
    assert settings.log_level == "DEBUG"
    assert settings.log_format == "json"
    assert settings.http_max_connections == 30
    assert settings.semantic_scholar_rate_limit_period_seconds == 5


def test_semantic_scholar_api_key_is_optional() -> None:
    """Anonymous Semantic Scholar access should be supported."""

    settings = Settings(
        _env_file=None,
        SEMANTIC_SCHOLAR_API_KEY="",
    )

    assert settings.semantic_scholar_api_key_value() is None


def test_semantic_scholar_api_key_can_be_read_safely() -> None:
    """Configured API keys should be available only through the helper."""

    settings = Settings(
        _env_file=None,
        SEMANTIC_SCHOLAR_API_KEY="test-secret-key",
    )

    assert settings.semantic_scholar_api_key_value() == "test-secret-key"

    assert "test-secret-key" not in repr(settings.semantic_scholar_api_key)


def test_keepalive_connections_cannot_exceed_total() -> None:
    """Keep-alive capacity must not exceed total connections."""

    with pytest.raises(
        ValidationError,
        match="cannot exceed HTTP_MAX_CONNECTIONS",
    ):
        Settings(
            _env_file=None,
            HTTP_MAX_CONNECTIONS=5,
            HTTP_MAX_KEEPALIVE_CONNECTIONS=10,
        )


def test_retry_minimum_cannot_exceed_maximum() -> None:
    """Retry delay bounds must form a valid range."""

    with pytest.raises(
        ValidationError,
        match="cannot exceed SEMANTIC_SCHOLAR_RETRY_MAX_SECONDS",
    ):
        Settings(
            _env_file=None,
            SEMANTIC_SCHOLAR_RETRY_MIN_SECONDS=30,
            SEMANTIC_SCHOLAR_RETRY_MAX_SECONDS=10,
        )


def test_get_settings_returns_cached_instance() -> None:
    """The settings dependency should be cached."""

    clear_settings_cache()

    first = get_settings()
    second = get_settings()

    assert first is second

    clear_settings_cache()


def test_auth_disabled_by_default() -> None:
    """Authentication must stay off unless explicitly enabled."""

    settings = Settings(_env_file=None)

    assert settings.auth_enabled is False
    assert settings.auth_issuer is None
    assert settings.auth_jwt_algorithms_list() == ["RS256"]
    assert settings.auth_required_scopes_list() == ["research-intelligence/invoke"]


def test_mcp_transport_accepts_streamable_http() -> None:
    """The streamable-http transport must be a valid configuration."""

    settings = Settings(_env_file=None, MCP_TRANSPORT="streamable-http")

    assert settings.mcp_transport == "streamable-http"


def test_auth_requires_issuer_when_enabled() -> None:
    """Enabling auth without an issuer must fail fast."""

    with pytest.raises(ValidationError, match="AUTH_ISSUER is required"):
        Settings(
            _env_file=None,
            AUTH_ENABLED=True,
            AUTH_AUDIENCE="research-intelligence-mcp",
            AUTH_JWT_SECRET="s",
            AUTH_JWT_ALGORITHMS="HS256",
        )


def test_auth_requires_audience_when_enabled() -> None:
    """Enabling auth without an audience must fail fast."""

    with pytest.raises(ValidationError, match="AUTH_AUDIENCE is required"):
        Settings(
            _env_file=None,
            AUTH_ENABLED=True,
            AUTH_ISSUER="https://auth.researchmind.ai",
            AUTH_JWT_SECRET="s",
            AUTH_JWT_ALGORITHMS="HS256",
        )


def test_auth_hs256_requires_secret() -> None:
    """HS256 verification must have a configured shared secret."""

    with pytest.raises(ValidationError, match="AUTH_JWT_SECRET is required"):
        Settings(
            _env_file=None,
            AUTH_ENABLED=True,
            AUTH_ISSUER="https://auth.researchmind.ai",
            AUTH_AUDIENCE="research-intelligence-mcp",
            AUTH_JWT_ALGORITHMS="HS256",
        )


def test_auth_asymmetric_algorithm_requires_jwks_url() -> None:
    """RS256/ES256/PS256 verification must have a configured JWKS endpoint."""

    with pytest.raises(ValidationError, match="AUTH_JWKS_URL is required"):
        Settings(
            _env_file=None,
            AUTH_ENABLED=True,
            AUTH_ISSUER="https://auth.researchmind.ai",
            AUTH_AUDIENCE="research-intelligence-mcp",
            AUTH_JWT_ALGORITHMS="RS256",
        )


def test_auth_valid_hs256_configuration_is_accepted() -> None:
    """A complete HS256 configuration should construct without error."""

    settings = Settings(
        _env_file=None,
        AUTH_ENABLED=True,
        AUTH_ISSUER="https://auth.researchmind.ai",
        AUTH_AUDIENCE="research-intelligence-mcp",
        AUTH_JWT_ALGORITHMS="HS256",
        AUTH_JWT_SECRET="a-sufficiently-long-shared-secret",
    )

    assert settings.auth_enabled is True
    assert settings.auth_jwt_secret_value() == "a-sufficiently-long-shared-secret"


def test_auth_valid_jwks_configuration_is_accepted() -> None:
    """A complete JWKS-backed configuration should construct without error."""

    settings = Settings(
        _env_file=None,
        AUTH_ENABLED=True,
        AUTH_ISSUER="https://auth.researchmind.ai",
        AUTH_AUDIENCE="research-intelligence-mcp",
        AUTH_JWT_ALGORITHMS="RS256",
        AUTH_JWKS_URL="https://auth.researchmind.ai/.well-known/jwks.json",
    )

    assert settings.auth_enabled is True
    assert settings.auth_jwt_secret_value() is None


def test_auth_algorithms_can_be_comma_separated() -> None:
    """List settings should accept comma-separated environment values."""

    settings = Settings(
        _env_file=None,
        AUTH_JWT_ALGORITHMS="RS256, ES256",
        AUTH_REQUIRED_SCOPES=(
            "research-intelligence/invoke, research-intelligence/search"
        ),
    )

    assert settings.auth_jwt_algorithms_list() == ["RS256", "ES256"]
    assert settings.auth_required_scopes_list() == [
        "research-intelligence/invoke",
        "research-intelligence/search",
    ]


def test_env_example_loads_without_error() -> None:
    """.env.example (the template users copy to .env) must always parse.

    Regression test for a real failure: comma-separated list fields and
    blank optional URL fields in .env.example previously broke settings
    loading entirely once a real .env was created from the template.
    """

    settings = Settings(_env_file=".env.example")

    assert settings.auth_enabled is False
    assert settings.mcp_transport == "stdio"


def test_blank_optional_url_env_vars_are_treated_as_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty-string optional URL env vars (as in .env.example) must not fail.

    Regression test: `.env.example` documents AUTH_JWKS_URL and
    AUTH_RESOURCE_SERVER_URL as present-but-blank by default. Without
    `env_ignore_empty`, pydantic rejects an empty string as an invalid URL
    for `HttpUrl | None` fields instead of falling back to `None`.
    """

    monkeypatch.setenv("AUTH_JWKS_URL", "")
    monkeypatch.setenv("AUTH_RESOURCE_SERVER_URL", "")

    settings = Settings(_env_file=None)

    assert settings.auth_jwks_url is None
    assert settings.auth_resource_server_url is None


def test_auth_jwt_secret_is_not_exposed_in_repr() -> None:
    """The shared secret must not leak through the default settings repr."""

    settings = Settings(
        _env_file=None,
        AUTH_JWT_SECRET="super-secret-value",
    )

    assert "super-secret-value" not in repr(settings.auth_jwt_secret)
