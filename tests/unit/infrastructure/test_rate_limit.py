"""Tests for asynchronous rate-limiting infrastructure."""

import asyncio

import pytest

from research_intelligence_mcp.infrastructure.rate_limit import (
    AsyncRateLimiter,
    UnlimitedRateLimiter,
)


@pytest.mark.asyncio
async def test_unlimited_rate_limiter_enters_immediately() -> None:
    """The no-op limiter should not block execution."""

    limiter = UnlimitedRateLimiter()

    async with limiter.limit():
        executed = True

    assert executed is True


@pytest.mark.asyncio
async def test_async_rate_limiter_allows_request() -> None:
    """A valid rate limiter should permit an available request."""

    limiter = AsyncRateLimiter(
        max_rate=1,
        time_period_seconds=0.01,
    )

    async with limiter.limit():
        executed = True

    assert executed is True


def test_async_rate_limiter_rejects_invalid_rate() -> None:
    """The maximum rate must be positive."""

    with pytest.raises(
        ValueError,
        match="max_rate must be at least 1",
    ):
        AsyncRateLimiter(
            max_rate=0,
            time_period_seconds=1,
        )


def test_async_rate_limiter_rejects_invalid_period() -> None:
    """The limiting period must be positive."""

    with pytest.raises(
        ValueError,
        match="time_period_seconds must be greater than zero",
    ):
        AsyncRateLimiter(
            max_rate=1,
            time_period_seconds=0,
        )


@pytest.mark.asyncio
async def test_async_rate_limiter_throttles_second_entry() -> None:
    """A second entry should wait when capacity has been consumed."""

    limiter = AsyncRateLimiter(
        max_rate=1,
        time_period_seconds=0.02,
    )

    async with limiter.limit():
        pass

    start = asyncio.get_running_loop().time()

    async with limiter.limit():
        pass

    elapsed = asyncio.get_running_loop().time() - start

    assert elapsed >= 0.01
