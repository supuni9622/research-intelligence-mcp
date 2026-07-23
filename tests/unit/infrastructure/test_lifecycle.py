"""Tests for application lifecycle state and ASGI shutdown middleware."""

from __future__ import annotations

from typing import Any

import pytest

from research_intelligence_mcp.infrastructure.lifecycle import (
    LifecycleState,
    LifespanShutdownMiddleware,
)


def test_lifecycle_state_starts_ready() -> None:
    """A freshly created lifecycle state should report ready."""

    lifecycle = LifecycleState()

    assert lifecycle.is_ready is True


def test_lifecycle_state_marks_shutting_down() -> None:
    """Marking shutdown should flip readiness and stay flipped."""

    lifecycle = LifecycleState()

    lifecycle.mark_shutting_down()

    assert lifecycle.is_ready is False

    lifecycle.mark_shutting_down()

    assert lifecycle.is_ready is False


class StubDependencies:
    """Records whether ``close`` was awaited, and how many times."""

    def __init__(self) -> None:
        self.close_calls = 0

    async def close(self) -> None:
        """Record one closure call."""

        self.close_calls += 1


async def _lifespan_app(
    scope: dict[str, Any],
    receive: Any,
    send: Any,
) -> None:
    """Minimal ASGI lifespan app: startup then shutdown, no extra behavior."""

    while True:
        message = await receive()

        if message["type"] == "lifespan.startup":
            await send({"type": "lifespan.startup.complete"})
        elif message["type"] == "lifespan.shutdown":
            await send({"type": "lifespan.shutdown.complete"})
            return


def _build_lifespan_messages() -> list[dict[str, str]]:
    return [
        {"type": "lifespan.startup"},
        {"type": "lifespan.shutdown"},
    ]


@pytest.mark.asyncio
async def test_lifespan_shutdown_middleware_closes_dependencies_once() -> None:
    """Shutdown should mark the lifecycle state and close dependencies once."""

    dependencies = StubDependencies()
    lifecycle = LifecycleState()

    middleware = LifespanShutdownMiddleware(
        _lifespan_app,
        dependencies=dependencies,  # type: ignore[arg-type]
        lifecycle=lifecycle,
    )

    messages = _build_lifespan_messages()
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return messages.pop(0)

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    assert lifecycle.is_ready is True

    await middleware({"type": "lifespan"}, receive, send)

    assert lifecycle.is_ready is False
    assert dependencies.close_calls == 1
    assert sent == [
        {"type": "lifespan.startup.complete"},
        {"type": "lifespan.shutdown.complete"},
    ]


@pytest.mark.asyncio
async def test_lifespan_shutdown_middleware_marks_shutdown_before_forwarding() -> None:
    """Readiness should flip as soon as the shutdown message is observed."""

    dependencies = StubDependencies()
    lifecycle = LifecycleState()
    observed_ready_during_app: list[bool] = []

    async def observing_app(
        scope: dict[str, Any],
        receive: Any,
        send: Any,
    ) -> None:
        await receive()  # startup
        await send({"type": "lifespan.startup.complete"})

        await receive()  # shutdown — readiness must already be flipped
        observed_ready_during_app.append(lifecycle.is_ready)
        await send({"type": "lifespan.shutdown.complete"})

    middleware = LifespanShutdownMiddleware(
        observing_app,
        dependencies=dependencies,  # type: ignore[arg-type]
        lifecycle=lifecycle,
    )

    messages = _build_lifespan_messages()

    async def receive() -> dict[str, Any]:
        return messages.pop(0)

    async def send(message: dict[str, Any]) -> None:
        return None

    await middleware({"type": "lifespan"}, receive, send)

    assert observed_ready_during_app == [False]


@pytest.mark.asyncio
async def test_lifespan_shutdown_middleware_passes_through_non_lifespan_scopes() -> (
    None
):
    """HTTP (and other non-lifespan) scopes must reach the wrapped app untouched."""

    dependencies = StubDependencies()
    lifecycle = LifecycleState()
    calls: list[dict[str, Any]] = []

    async def http_app(scope: dict[str, Any], receive: Any, send: Any) -> None:
        calls.append(scope)

    middleware = LifespanShutdownMiddleware(
        http_app,
        dependencies=dependencies,  # type: ignore[arg-type]
        lifecycle=lifecycle,
    )

    async def receive() -> dict[str, Any]:
        raise AssertionError("receive should not be called for http scopes")

    async def send(message: dict[str, Any]) -> None:
        raise AssertionError("send should not be called for http scopes")

    await middleware({"type": "http", "path": "/health"}, receive, send)

    assert calls == [{"type": "http", "path": "/health"}]
    assert dependencies.close_calls == 0
    assert lifecycle.is_ready is True
