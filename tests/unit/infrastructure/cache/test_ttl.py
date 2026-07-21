"""Tests for the asynchronous bounded TTL cache."""

from __future__ import annotations

import pytest

from research_intelligence_mcp.infrastructure.cache.ttl import (
    AsyncBoundedTTLCache,
)


class FakeTimer:
    """Controllable monotonic timer for TTL tests."""

    def __init__(self) -> None:
        self.current = 0.0

    def __call__(self) -> float:
        return self.current

    def advance(
        self,
        seconds: float,
    ) -> None:
        """Advance the fake clock."""

        self.current += seconds


def test_cache_rejects_invalid_configuration() -> None:
    """Cache bounds and TTL must be positive."""

    with pytest.raises(ValueError):
        AsyncBoundedTTLCache[str, str](
            max_size=0,
            ttl_seconds=60,
        )

    with pytest.raises(ValueError):
        AsyncBoundedTTLCache[str, str](
            max_size=10,
            ttl_seconds=0,
        )


@pytest.mark.asyncio
async def test_cache_records_miss_then_hit() -> None:
    """Cache lookups should update hit and miss statistics."""

    cache = AsyncBoundedTTLCache[str, str](
        max_size=10,
        ttl_seconds=60,
    )

    missing = await cache.get("paper")

    assert missing.found is False
    assert missing.value is None

    await cache.set(
        "paper",
        "cached-paper",
    )

    found = await cache.get("paper")

    assert found.found is True
    assert found.value == "cached-paper"

    stats = await cache.stats()

    assert stats.hits == 1
    assert stats.misses == 1
    assert stats.writes == 1
    assert stats.current_size == 1
    assert stats.hit_ratio == 0.5


@pytest.mark.asyncio
async def test_cache_expires_entries_after_ttl() -> None:
    """Expired entries should become cache misses."""

    timer = FakeTimer()

    cache = AsyncBoundedTTLCache[str, str](
        max_size=10,
        ttl_seconds=10,
        timer=timer,
    )

    await cache.set(
        "paper",
        "cached-paper",
    )

    timer.advance(11)

    result = await cache.get("paper")

    assert result.found is False

    stats = await cache.stats()

    assert stats.expirations == 1
    assert stats.current_size == 0


@pytest.mark.asyncio
async def test_cache_evicts_least_recently_used_entry() -> None:
    """A full cache should evict its least recently used entry."""

    cache = AsyncBoundedTTLCache[str, str](
        max_size=2,
        ttl_seconds=60,
    )

    await cache.set(
        "first",
        "one",
    )

    await cache.set(
        "second",
        "two",
    )

    await cache.get("first")

    await cache.set(
        "third",
        "three",
    )

    first = await cache.get("first")
    second = await cache.get("second")
    third = await cache.get("third")

    assert first.found is True
    assert second.found is False
    assert third.found is True

    stats = await cache.stats()

    assert stats.evictions == 1
    assert stats.current_size == 2


@pytest.mark.asyncio
async def test_cache_delete_and_clear() -> None:
    """Entries should support explicit deletion and clearing."""

    cache = AsyncBoundedTTLCache[str, str](
        max_size=10,
        ttl_seconds=60,
    )

    await cache.set(
        "first",
        "one",
    )

    await cache.set(
        "second",
        "two",
    )

    assert await cache.delete("first") is True
    assert await cache.delete("missing") is False

    await cache.clear()

    stats = await cache.stats()

    assert stats.current_size == 0
