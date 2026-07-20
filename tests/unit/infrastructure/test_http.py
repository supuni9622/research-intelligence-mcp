"""Tests for shared asynchronous HTTP infrastructure."""

import httpx
import pytest

from research_intelligence_mcp.config.settings import Settings
from research_intelligence_mcp.infrastructure.http import (
    build_httpx_limits,
    build_httpx_timeout,
    create_async_http_client,
    wrap_async_http_client,
)
from research_intelligence_mcp.infrastructure.rate_limit import (
    UnlimitedRateLimiter,
)


def build_test_settings() -> Settings:
    """Build deterministic settings for infrastructure tests."""

    return Settings(
        _env_file=None,
        HTTP_CONNECT_TIMEOUT_SECONDS=2,
        HTTP_READ_TIMEOUT_SECONDS=10,
        HTTP_WRITE_TIMEOUT_SECONDS=8,
        HTTP_POOL_TIMEOUT_SECONDS=3,
        HTTP_MAX_CONNECTIONS=15,
        HTTP_MAX_KEEPALIVE_CONNECTIONS=5,
        HTTP_KEEPALIVE_EXPIRY_SECONDS=20,
        HTTP_USER_AGENT="research-intelligence-mcp-test/0.1.0",
    )


def test_build_httpx_timeout() -> None:
    """Timeout settings should map to granular HTTPX values."""

    settings = build_test_settings()

    timeout = build_httpx_timeout(settings)

    assert timeout.connect == 2
    assert timeout.read == 10
    assert timeout.write == 8
    assert timeout.pool == 3


def test_build_httpx_limits() -> None:
    """Connection settings should map to HTTPX limits."""

    settings = build_test_settings()

    limits = build_httpx_limits(settings)

    assert limits.max_connections == 15
    assert limits.max_keepalive_connections == 5
    assert limits.keepalive_expiry == 20


@pytest.mark.asyncio
async def test_http_client_executes_get_request() -> None:
    """The wrapper should execute GET requests through HTTPX."""

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.headers["user-agent"] == ("research-intelligence-mcp-test/0.1.0")

        return httpx.Response(
            status_code=200,
            json={"status": "ok"},
        )

    transport = httpx.MockTransport(handler)

    client = create_async_http_client(
        settings=build_test_settings(),
        rate_limiter=UnlimitedRateLimiter(),
        base_url="https://example.test",
        transport=transport,
    )

    try:
        response = await client.get(
            "/papers",
            params={"query": "RAG"},
        )
    finally:
        await client.close()

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert client.is_closed is True


@pytest.mark.asyncio
async def test_http_client_executes_post_request() -> None:
    """The wrapper should send JSON request bodies."""

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        body = await request.aread()

        assert body == b'{"paperIds":["paper-1"]}'

        return httpx.Response(
            status_code=200,
            json={"recommendedPapers": []},
        )

    transport = httpx.MockTransport(handler)

    client = create_async_http_client(
        settings=build_test_settings(),
        rate_limiter=UnlimitedRateLimiter(),
        base_url="https://example.test",
        transport=transport,
    )

    async with client:
        response = await client.post(
            "/recommendations",
            json={
                "paperIds": ["paper-1"],
            },
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_http_client_does_not_raise_for_http_status() -> None:
    """Provider clients should classify HTTP status responses."""

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=429,
            json={
                "message": "Too Many Requests",
                "code": "429",
            },
        )

    client = create_async_http_client(
        settings=build_test_settings(),
        rate_limiter=UnlimitedRateLimiter(),
        base_url="https://example.test",
        transport=httpx.MockTransport(handler),
    )

    async with client:
        response = await client.get("/papers")

    assert response.status_code == 429
    assert response.json()["code"] == "429"


@pytest.mark.asyncio
async def test_http_client_propagates_timeout() -> None:
    """Transport timeout exceptions should remain classifiable upstream."""

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        raise httpx.ReadTimeout(
            "Request timed out.",
            request=request,
        )

    client = create_async_http_client(
        settings=build_test_settings(),
        rate_limiter=UnlimitedRateLimiter(),
        base_url="https://example.test",
        transport=httpx.MockTransport(handler),
    )

    async with client:
        with pytest.raises(httpx.ReadTimeout):
            await client.get("/papers")


@pytest.mark.asyncio
async def test_wrapped_external_client_is_not_closed() -> None:
    """The wrapper must not close externally managed clients."""

    external_client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                status_code=200,
                json={"ok": True},
            )
        )
    )

    wrapper = wrap_async_http_client(
        client=external_client,
        rate_limiter=UnlimitedRateLimiter(),
    )

    await wrapper.close()

    assert wrapper.is_closed is True
    assert external_client.is_closed is False

    await external_client.aclose()


@pytest.mark.asyncio
async def test_closed_http_client_rejects_requests() -> None:
    """Requests cannot execute after the wrapper is closed."""

    client = create_async_http_client(
        settings=build_test_settings(),
        rate_limiter=UnlimitedRateLimiter(),
        base_url="https://example.test",
        transport=httpx.MockTransport(lambda request: httpx.Response(status_code=200)),
    )

    await client.close()

    with pytest.raises(
        RuntimeError,
        match="HTTP client is already closed",
    ):
        await client.get("/papers")
