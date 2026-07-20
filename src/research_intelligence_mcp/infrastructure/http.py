"""Shared asynchronous HTTP client infrastructure."""

from collections.abc import Mapping
from types import TracebackType
from typing import Any, Self

import httpx

from research_intelligence_mcp.config.settings import Settings
from research_intelligence_mcp.infrastructure.logging import get_logger
from research_intelligence_mcp.infrastructure.rate_limit import RateLimiter

logger = get_logger(__name__)

JsonObject = Mapping[str, Any]
QueryParameters = Mapping[
    str,
    str | int | float | bool | None,
]


class AsyncHttpClient:
    """Managed async HTTP client with optional local rate limiting.

    The client owns a reusable `httpx.AsyncClient` unless an existing client
    is injected for testing.
    """

    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        rate_limiter: RateLimiter,
        owns_client: bool,
    ) -> None:
        self._client = client
        self._rate_limiter = rate_limiter
        self._owns_client = owns_client
        self._closed = False

    @property
    def raw_client(self) -> httpx.AsyncClient:
        """Return the underlying HTTPX client.

        This property is primarily available for advanced provider operations
        and testing. Normal provider clients should use `request`.
        """

        return self._client

    @property
    def is_closed(self) -> bool:
        """Return whether this wrapper has been closed."""

        return self._closed or self._client.is_closed

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: QueryParameters | None = None,
        headers: Mapping[str, str] | None = None,
        json: Any | None = None,
    ) -> httpx.Response:
        """Execute a rate-limited HTTP request.

        HTTP status codes are not converted into exceptions here. Provider
        clients must inspect the response and apply provider-specific error
        normalization and retry policies.

        Args:
            method: HTTP request method.
            url: Absolute or client-relative request URL.
            params: Optional query parameters.
            headers: Optional per-request headers.
            json: Optional JSON-compatible request body.

        Returns:
            Raw HTTPX response.

        Raises:
            RuntimeError: If the client has already been closed.
            httpx.RequestError: For transport-level failures.
        """

        if self.is_closed:
            raise RuntimeError("HTTP client is already closed.")

        normalized_method = method.upper()

        logger.debug(
            "http_request_started",
            method=normalized_method,
            url=url,
        )

        async with self._rate_limiter.limit():
            try:
                response = await self._client.request(
                    method=normalized_method,
                    url=url,
                    params=params,
                    headers=headers,
                    json=json,
                )
            except httpx.TimeoutException:
                logger.warning(
                    "http_request_timed_out",
                    method=normalized_method,
                    url=url,
                )
                raise
            except httpx.RequestError:
                logger.warning(
                    "http_request_transport_failed",
                    method=normalized_method,
                    url=url,
                )
                raise

        logger.debug(
            "http_request_completed",
            method=normalized_method,
            url=url,
            status_code=response.status_code,
        )

        return response

    async def get(
        self,
        url: str,
        *,
        params: QueryParameters | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        """Execute a GET request."""

        return await self.request(
            method="GET",
            url=url,
            params=params,
            headers=headers,
        )

    async def post(
        self,
        url: str,
        *,
        params: QueryParameters | None = None,
        headers: Mapping[str, str] | None = None,
        json: Any | None = None,
    ) -> httpx.Response:
        """Execute a POST request."""

        return await self.request(
            method="POST",
            url=url,
            params=params,
            headers=headers,
            json=json,
        )

    async def close(self) -> None:
        """Close the underlying client when this wrapper owns it."""

        if self._closed:
            return

        if self._owns_client and not self._client.is_closed:
            await self._client.aclose()

        self._closed = True

        logger.debug("http_client_closed")

    async def __aenter__(self) -> Self:
        """Enter the managed client context."""

        if self.is_closed:
            raise RuntimeError("HTTP client is already closed.")

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the managed client when leaving its context."""

        await self.close()


def build_httpx_timeout(settings: Settings) -> httpx.Timeout:
    """Build granular HTTPX timeout configuration."""

    return httpx.Timeout(
        connect=settings.http_connect_timeout_seconds,
        read=settings.http_read_timeout_seconds,
        write=settings.http_write_timeout_seconds,
        pool=settings.http_pool_timeout_seconds,
    )


def build_httpx_limits(settings: Settings) -> httpx.Limits:
    """Build HTTPX connection-pool limits."""

    return httpx.Limits(
        max_connections=settings.http_max_connections,
        max_keepalive_connections=(settings.http_max_keepalive_connections),
        keepalive_expiry=settings.http_keepalive_expiry_seconds,
    )


def create_async_http_client(
    *,
    settings: Settings,
    rate_limiter: RateLimiter,
    base_url: str = "",
    default_headers: Mapping[str, str] | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> AsyncHttpClient:
    """Create a managed shared HTTP client.

    Args:
        settings: Validated application settings.
        rate_limiter: Local limiter applied before every request.
        base_url: Optional base URL used by HTTPX.
        default_headers: Optional default request headers.
        transport: Optional HTTPX transport, primarily for tests.

    Returns:
        Managed asynchronous HTTP client.
    """

    headers = {
        "Accept": "application/json",
        "User-Agent": settings.http_user_agent,
    }

    if default_headers is not None:
        headers.update(default_headers)

    client = httpx.AsyncClient(
        base_url=base_url,
        headers=headers,
        timeout=build_httpx_timeout(settings),
        limits=build_httpx_limits(settings),
        follow_redirects=False,
        transport=transport,
    )

    return AsyncHttpClient(
        client=client,
        rate_limiter=rate_limiter,
        owns_client=True,
    )


def wrap_async_http_client(
    *,
    client: httpx.AsyncClient,
    rate_limiter: RateLimiter,
) -> AsyncHttpClient:
    """Wrap an externally managed HTTPX client.

    The wrapper does not close externally owned clients. This is useful for
    tests and integrations that already manage an HTTPX lifecycle.
    """

    return AsyncHttpClient(
        client=client,
        rate_limiter=rate_limiter,
        owns_client=False,
    )
