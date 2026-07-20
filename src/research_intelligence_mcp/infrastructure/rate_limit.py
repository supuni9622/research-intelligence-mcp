"""Async client-side rate-limiting infrastructure."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Protocol

from aiolimiter import AsyncLimiter


class RateLimiter(Protocol):
    """Protocol implemented by asynchronous request limiters."""

    @asynccontextmanager
    async def limit(self) -> AsyncIterator[None]:
        """Wait until execution is permitted by the limiter."""

        yield


class AsyncRateLimiter:
    """Leaky-bucket asynchronous request-rate limiter."""

    def __init__(
        self,
        *,
        max_rate: int,
        time_period_seconds: float,
    ) -> None:
        """Create a local asynchronous limiter.

        Args:
            max_rate: Maximum entries allowed during the configured period.
            time_period_seconds: Length of the limiting period in seconds.
        """

        if max_rate < 1:
            raise ValueError("max_rate must be at least 1.")

        if time_period_seconds <= 0:
            raise ValueError("time_period_seconds must be greater than zero.")

        self._limiter = AsyncLimiter(
            max_rate=max_rate,
            time_period=time_period_seconds,
        )

    @asynccontextmanager
    async def limit(self) -> AsyncIterator[None]:
        """Wait for capacity and enter the rate-limited section."""

        async with self._limiter:
            yield


class UnlimitedRateLimiter:
    """No-op rate limiter for tests and unrestricted integrations."""

    @asynccontextmanager
    async def limit(self) -> AsyncIterator[None]:
        """Enter immediately without applying throttling."""

        yield
