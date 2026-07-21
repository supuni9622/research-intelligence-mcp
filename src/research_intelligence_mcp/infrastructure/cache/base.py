"""Provider-neutral asynchronous cache contracts and statistics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(
    frozen=True,
    slots=True,
)
class CacheLookup[ValueT]:
    """Result of one cache lookup.

    A dedicated lookup model avoids using ``None`` as a cache-miss sentinel,
    allowing caches to store values that may themselves be ``None``.
    """

    found: bool
    value: ValueT | None = None


@dataclass(
    frozen=True,
    slots=True,
)
class CacheStats:
    """Immutable snapshot of cache activity."""

    hits: int
    misses: int
    writes: int
    evictions: int
    expirations: int
    current_size: int
    max_size: int

    @property
    def requests(self) -> int:
        """Return the total number of cache lookup requests."""

        return self.hits + self.misses

    @property
    def hit_ratio(self) -> float:
        """Return cache-hit ratio as a value between zero and one."""

        if self.requests == 0:
            return 0.0

        return self.hits / self.requests


class AsyncCache[KeyT, ValueT](Protocol):
    """Asynchronous bounded-cache contract."""

    async def get(
        self,
        key: KeyT,
    ) -> CacheLookup[ValueT]:
        """Retrieve a value by key."""

        ...

    async def set(
        self,
        key: KeyT,
        value: ValueT,
    ) -> None:
        """Store a value by key."""

        ...

    async def delete(
        self,
        key: KeyT,
    ) -> bool:
        """Delete a value and report whether it existed."""

        ...

    async def clear(self) -> None:
        """Remove every cached value."""

        ...

    async def stats(self) -> CacheStats:
        """Return a consistent statistics snapshot."""

        ...
