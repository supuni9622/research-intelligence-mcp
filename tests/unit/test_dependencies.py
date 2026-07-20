"""Tests for the application dependency container."""

from research_intelligence_mcp.config.settings import Settings
from research_intelligence_mcp.mcp.dependencies import (
    AppDependencies,
    build_dependencies,
)


def test_build_dependencies_preserves_settings_instance() -> None:
    """The dependency container should hold validated application settings."""

    settings = Settings(
        _env_file=None,
        APP_ENVIRONMENT="test",
    )

    dependencies = build_dependencies(settings=settings)

    assert isinstance(dependencies, AppDependencies)
    assert dependencies.settings is settings
    assert dependencies.settings.app_environment == "test"
