"""Validated application settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
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
        extra="ignore",
        frozen=True,
    )

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

    mcp_server_name: str = Field(
        default="research-intelligence-mcp",
        validation_alias="MCP_SERVER_NAME",
    )

    mcp_transport: MCPTransport = Field(
        default="stdio",
        validation_alias="MCP_TRANSPORT",
    )

    log_level: LogLevel = Field(
        default="INFO",
        validation_alias="LOG_LEVEL",
    )

    log_format: LogFormat = Field(
        default="console",
        validation_alias="LOG_FORMAT",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings."""

    return Settings()


def clear_settings_cache() -> None:
    """Clear cached settings.

    This is mainly useful when tests change environment variables.
    """

    get_settings.cache_clear()
