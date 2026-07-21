"""Async-safe bounded TTL cache implementation."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from time import monotonic

from cachetools import TTLCache

from research_intelligence_mcp.infrastructure.cache.base import (
    CacheLookup,
    CacheStats,
)


class AsyncBoundedTTLCache[KeyT, ValueT]:
    """Async-safe TTL cache with bounded LRU eviction.

    ``cachetools.TTLCache`` expires stale entries by TTL and evicts the least
    recently used live entry when the configured maximum size is reached.

    The underlying cache is protected by an asyncio lock because cachetools
    collections are not thread-safe.
    """

    def __init__(
        self,
        *,
        max_size: int,
        ttl_seconds: float,
        timer: Callable[[], float] = monotonic,
    ) -> None:
        """Initialize a bounded TTL cache."""

        if max_size < 1:
            raise ValueError("Cache max_size must be at least one.")

        if ttl_seconds <= 0:
            raise ValueError("Cache ttl_seconds must be greater than zero.")

        self._max_size = max_size
        self._ttl_seconds = ttl_seconds

        self._cache: TTLCache[KeyT, ValueT] = TTLCache(
            maxsize=max_size,
            ttl=ttl_seconds,
            timer=timer,
        )

        self._lock = asyncio.Lock()

        self._hits = 0
        self._misses = 0
        self._writes = 0
        self._evictions = 0
        self._expirations = 0

    @property
    def max_size(self) -> int:
        """Return the maximum number of live entries."""

        return self._max_size

    @property
    def ttl_seconds(self) -> float:
        """Return the configured entry TTL."""

        return self._ttl_seconds

    async def get(
        self,
        key: KeyT,
    ) -> CacheLookup[ValueT]:
        """Retrieve a live cached value."""

        async with self._lock:
            self._expire_locked()

            try:
                value = self._cache[key]
            except KeyError:
                self._misses += 1

                return CacheLookup(
                    found=False,
                    value=None,
                )

            self._hits += 1

            return CacheLookup(
                found=True,
                value=value,
            )

    async def set(
        self,
        key: KeyT,
        value: ValueT,
    ) -> None:
        """Store a value and evict the least recently used entry if needed."""

        async with self._lock:
            self._expire_locked()

            key_already_exists = key in self._cache
            cache_is_full = len(self._cache) >= self._max_size

            if not key_already_exists and cache_is_full:
                self._evictions += 1

            self._cache[key] = value
            self._writes += 1

    async def delete(
        self,
        key: KeyT,
    ) -> bool:
        """Delete one cached entry."""

        async with self._lock:
            self._expire_locked()

            try:
                del self._cache[key]
            except KeyError:
                return False

            return True

    async def clear(self) -> None:
        """Remove all entries without resetting lifetime statistics."""

        async with self._lock:
            self._cache.clear()

    async def stats(self) -> CacheStats:
        """Return a consistent cache statistics snapshot."""

        async with self._lock:
            self._expire_locked()

            return CacheStats(
                hits=self._hits,
                misses=self._misses,
                writes=self._writes,
                evictions=self._evictions,
                expirations=self._expirations,
                current_size=len(self._cache),
                max_size=self._max_size,
            )

    def _expire_locked(self) -> None:
        """Expire stale entries while the caller holds the cache lock."""

        size_before = len(self._cache)

        self._cache.expire()

        size_after = len(self._cache)

        self._expirations += size_before - size_after
