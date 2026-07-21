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
    """Async-safe bounded in-memory cache with TTL and LRU eviction.

    The underlying ``TTLCache`` provides:

    - time-based expiration;
    - bounded capacity;
    - least-recently-used eviction.

    This wrapper adds:

    - asynchronous lock protection;
    - explicit cache statistics;
    - deterministic expiration accounting.
    """

    def __init__(
        self,
        *,
        max_size: int,
        ttl_seconds: float,
        timer: Callable[[], float] = monotonic,
    ) -> None:
        if max_size <= 0:
            msg = "max_size must be greater than zero"
            raise ValueError(msg)

        if ttl_seconds <= 0:
            msg = "ttl_seconds must be greater than zero"
            raise ValueError(msg)

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
        """Return the configured maximum number of cache entries."""

        return self._max_size

    @property
    def ttl_seconds(self) -> float:
        """Return the configured cache TTL in seconds."""

        return self._ttl_seconds

    async def get(
        self,
        key: KeyT,
    ) -> CacheLookup[ValueT]:
        """Return a cached value when present and not expired."""

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
        """Store a value in the cache.

        Expired entries are removed before determining whether insertion will
        require an LRU eviction.
        """

        async with self._lock:
            self._expire_locked()

            is_existing_key = key in self._cache
            cache_is_full = len(self._cache) >= self._max_size

            if not is_existing_key and cache_is_full:
                self._evictions += 1

            self._cache[key] = value
            self._writes += 1

    async def delete(
        self,
        key: KeyT,
    ) -> bool:
        """Delete a cache entry.

        Returns ``True`` when an active entry existed and was removed.
        """

        async with self._lock:
            self._expire_locked()

            try:
                del self._cache[key]
            except KeyError:
                return False

            return True

    async def clear(self) -> None:
        """Remove all cached entries without resetting accumulated metrics."""

        async with self._lock:
            self._cache.clear()

    async def stats(self) -> CacheStats:
        """Return a snapshot of cache statistics."""

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
        """Remove expired entries and update expiration statistics.

        This method must only be called while ``self._lock`` is held.

        ``TTLCache.expire()`` returns the expired key-value pairs. Counting
        those returned entries ensures expirations are not silently removed
        without being reflected in cache statistics.
        """

        expired_count = sum(
            1
            for _ in self._cache.expire()
        )

        self._expirations += expired_count