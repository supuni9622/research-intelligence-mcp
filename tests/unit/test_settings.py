"""Tests for application settings."""

import pytest

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


def test_settings_can_be_loaded_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Environment variables should override defaults."""

    monkeypatch.setenv("APP_ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_FORMAT", "json")

    settings = Settings(_env_file=None)

    assert settings.app_environment == "test"
    assert settings.log_level == "DEBUG"
    assert settings.log_format == "json"


def test_get_settings_returns_cached_instance() -> None:
    """The settings dependency should be cached."""

    clear_settings_cache()

    first = get_settings()
    second = get_settings()

    assert first is second

    clear_settings_cache()
