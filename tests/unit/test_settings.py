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
