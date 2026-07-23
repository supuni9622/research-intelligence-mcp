#!/usr/bin/env python3
"""Deployment smoke test for a running streamable-http MCP server.

Implements Milestone 9 (Deployment Smoke Tests) of
docs/remote_mcp_deployment_prd.md — Level 1 (local container) and Level 2
(ECS, from another private-VPC task) both use this same script, since both
just need a reachable base URL and, once auth is enabled, a bearer token.

Verifies, against ``--base-url``:

1. ``GET /health`` returns 200 with the expected liveness payload.
2. ``GET /ready`` returns 200 with the expected readiness payload.
3. ``GET /metrics`` returns Prometheus-formatted text.
4. An MCP session initializes over the streamable-http transport.
5. Tool discovery (``tools/list``) returns the expected tool set.
6. ``health_check`` can be invoked.
7. ``search_papers`` can be invoked with a small, bounded result limit.

Never prints the bearer token. Exits non-zero on any failure, with the
failing step named, so it is safe to gate a CI/CD pipeline on this script.

Example:

    uv run python deployment/scripts/smoke_test.py \\
        --base-url http://127.0.0.1:8000 \\
        --auth-token "$MCP_SERVICE_TOKEN"
"""

from __future__ import annotations

import argparse
import functools
import sys
from contextlib import AsyncExitStack

import anyio
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

EXPECTED_TOOLS = {
    "health_check",
    "search_papers",
    "get_paper",
    "get_paper_citations",
    "get_paper_references",
    "get_related_papers",
    "resolve_paper_access",
}

# Deliberately small and stable, per the "Test Safety" section of the PRD.
SMOKE_TEST_QUERY = "retrieval augmented generation"
SMOKE_TEST_LIMIT = 2


class SmokeTestFailure(Exception):
    """Raised with a step name and reason when a smoke-test step fails."""


def _check_http_endpoints(*, base_url: str, headers: dict[str, str]) -> None:
    with httpx.Client(base_url=base_url, timeout=10.0, headers=headers) as client:
        health = client.get("/health")
        if health.status_code != 200 or health.json().get("status") != "healthy":
            raise SmokeTestFailure(
                f"/health: unexpected response {health.status_code} {health.text}"
            )
        print("[ok] GET /health")

        ready = client.get("/ready")
        if ready.status_code != 200 or ready.json().get("status") != "ready":
            raise SmokeTestFailure(
                f"/ready: unexpected response {ready.status_code} {ready.text}"
            )
        print("[ok] GET /ready")

        metrics = client.get("/metrics")
        if metrics.status_code != 200 or "# HELP" not in metrics.text:
            raise SmokeTestFailure(
                f"/metrics: unexpected response {metrics.status_code}"
            )
        print("[ok] GET /metrics")


async def _check_mcp_session(*, base_url: str, headers: dict[str, str]) -> None:
    mcp_url = f"{base_url.rstrip('/')}/mcp"

    async with AsyncExitStack() as stack:
        http_client = await stack.enter_async_context(
            httpx.AsyncClient(headers=headers, timeout=30.0)
        )
        read_stream, write_stream, _ = await stack.enter_async_context(
            streamable_http_client(mcp_url, http_client=http_client)
        )
        session = await stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )

        await session.initialize()
        print("[ok] MCP session initialized")

        tools_result = await session.list_tools()
        tool_names = {tool.name for tool in tools_result.tools}

        missing = EXPECTED_TOOLS - tool_names
        if missing:
            raise SmokeTestFailure(
                f"tools/list: missing expected tools {sorted(missing)}"
            )
        print(f"[ok] tools/list returned {len(tool_names)} tools")

        health_result = await session.call_tool("health_check", {})
        if health_result.isError:
            raise SmokeTestFailure(
                f"health_check tool call failed: {health_result.content}"
            )
        print("[ok] health_check tool call")

        search_result = await session.call_tool(
            "search_papers",
            {"query": SMOKE_TEST_QUERY, "limit": SMOKE_TEST_LIMIT},
        )
        if search_result.isError:
            raise SmokeTestFailure(
                f"search_papers tool call failed: {search_result.content}"
            )
        print("[ok] search_papers tool call")


def run_smoke_test(*, base_url: str, auth_token: str | None) -> None:
    """Run every smoke-test step against a running server, in order."""

    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}

    _check_http_endpoints(base_url=base_url, headers=headers)
    anyio.run(functools.partial(_check_mcp_session, base_url=base_url, headers=headers))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Server base URL, without a trailing /mcp.",
    )
    parser.add_argument(
        "--auth-token",
        default=None,
        help=(
            "Bearer token for AUTH_ENABLED=true deployments. Never logged or "
            "printed. Omit for local unauthenticated development servers."
        ),
    )
    args = parser.parse_args()

    try:
        run_smoke_test(base_url=args.base_url, auth_token=args.auth_token)
    except SmokeTestFailure as exc:
        print(f"[fail] {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"[fail] unexpected error: {exc}", file=sys.stderr)
        sys.exit(1)

    print("smoke test passed")


if __name__ == "__main__":
    main()
