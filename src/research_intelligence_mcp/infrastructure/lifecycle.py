"""Application lifecycle state and ASGI graceful-shutdown wiring.

Implements the "Graceful Shutdown" and readiness requirements of
``docs/remote_mcp_deployment_prd.md``: ``/ready`` must flip to ``not_ready``
once shutdown begins, and every provider HTTP client must be closed exactly
once. Only the ``streamable-http`` transport uses
:class:`LifespanShutdownMiddleware`; ``stdio`` has no ASGI lifespan and closes
:class:`~research_intelligence_mcp.mcp.dependencies.AppDependencies` directly
from ``main.py``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, MutableMapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from research_intelligence_mcp.mcp.dependencies import AppDependencies

# Mirrors Starlette's own ASGI type aliases exactly (plain `Callable` aliases,
# not `Protocol` classes) so that a `Starlette` instance — whose `__call__`
# is typed against those same aliases — satisfies `ASGIApp` structurally
# without a cast.
type Scope = MutableMapping[str, Any]
type Message = MutableMapping[str, Any]
type Receive = Callable[[], Awaitable[Message]]
type Send = Callable[[Message], Awaitable[None]]
type ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


class LifecycleState:
    """Tracks whether the server is still accepting new work.

    A plain boolean attribute is sufficient here: it is only ever set once
    (startup shutdown is not reversible) and read from request handlers on
    the same event loop, so no additional locking is required.
    """

    def __init__(self) -> None:
        self._shutting_down = False

    @property
    def is_ready(self) -> bool:
        """Return whether the server should still be considered ready."""

        return not self._shutting_down

    def mark_shutting_down(self) -> None:
        """Record that graceful shutdown has begun."""

        self._shutting_down = True


class LifespanShutdownMiddleware:
    """ASGI middleware that flips readiness and closes dependencies on shutdown.

    Wraps the ASGI ``lifespan`` scope only; ``http`` and other scopes pass
    straight through unmodified. Marking ``lifecycle`` as shutting down
    happens as soon as the ``lifespan.shutdown`` message is observed, before
    it is even forwarded to the wrapped application.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        dependencies: AppDependencies,
        lifecycle: LifecycleState,
    ) -> None:
        self._app = app
        self._dependencies = dependencies
        self._lifecycle = lifecycle
        self._closed = False

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "lifespan":
            await self._app(scope, receive, send)
            return

        async def receive_wrapper() -> Message:
            message = await receive()

            if message.get("type") == "lifespan.shutdown":
                self._lifecycle.mark_shutting_down()

            return message

        try:
            await self._app(scope, receive_wrapper, send)
        finally:
            await self._close_once()

    async def _close_once(self) -> None:
        """Close dependencies at most once, even if shutdown runs twice."""

        if self._closed:
            return

        self._closed = True

        await self._dependencies.close()
