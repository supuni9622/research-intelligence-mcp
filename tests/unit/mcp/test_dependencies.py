"""Tests for application dependency composition."""

import pytest

from research_intelligence_mcp.config.settings import (
    Settings,
)
from research_intelligence_mcp.domain.enums import (
    ProviderName,
)
from research_intelligence_mcp.mcp.dependencies import (
    build_dependencies,
)
from research_intelligence_mcp.providers.cached import (
    CachedPaperProvider,
)


def build_test_settings() -> Settings:
    """Build isolated dependency-composition settings."""

    return Settings(
        _env_file=None,
        APP_ENVIRONMENT="test",
        CACHE_ENABLED=True,
        SEARCH_CACHE_MAX_SIZE=25,
        SEARCH_CACHE_TTL_SECONDS=60,
        PAPER_CACHE_MAX_SIZE=50,
        PAPER_CACHE_TTL_SECONDS=120,
    )


def test_build_dependencies_registers_cached_providers() -> None:
    """The provider registry should expose caching decorators."""

    dependencies = build_dependencies(
        settings=build_test_settings(),
    )

    semantic_scholar = dependencies.provider_registry.get(
        ProviderName.SEMANTIC_SCHOLAR,
    )

    arxiv = dependencies.provider_registry.get(
        ProviderName.ARXIV,
    )

    assert isinstance(
        semantic_scholar,
        CachedPaperProvider,
    )

    assert isinstance(
        arxiv,
        CachedPaperProvider,
    )


def test_build_dependencies_configures_cache_limits() -> None:
    """Cache instances should use configured capacity and TTL."""

    dependencies = build_dependencies(
        settings=build_test_settings(),
    )

    assert dependencies.search_cache.max_size == 25
    assert dependencies.search_cache.ttl_seconds == 60

    assert dependencies.paper_cache.max_size == 50
    assert dependencies.paper_cache.ttl_seconds == 120


@pytest.mark.asyncio
async def test_dependencies_close_clears_empty_caches() -> None:
    """Dependency shutdown should leave caches empty."""

    dependencies = build_dependencies(
        settings=build_test_settings(),
    )

    await dependencies.close()

    search_stats = await dependencies.search_cache.stats()
    paper_stats = await dependencies.paper_cache.stats()

    assert search_stats.current_size == 0
    assert paper_stats.current_size == 0
