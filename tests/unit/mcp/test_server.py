"""Tests for MCP server construction and tool registration."""

from __future__ import annotations

from typing import cast

import pytest

from research_intelligence_mcp.config.settings import (
    Settings,
)
from research_intelligence_mcp.mcp.dependencies import (
    AppDependencies,
)
from research_intelligence_mcp.mcp.server import (
    create_mcp_server,
)


class StubSearchService:
    """Unused federated service stand-in for registration tests."""

    async def search(
        self,
        request: object,
    ) -> object:
        """Fail if unexpectedly executed."""

        raise AssertionError("Search should not execute during registration.")


def build_server_dependencies() -> AppDependencies:
    """Build minimal dependencies required during server creation."""

    return cast(
        AppDependencies,
        type(
            "ServerDependencies",
            (),
            {
                "settings": Settings(
                    _env_file=None,
                    APP_ENVIRONMENT="test",
                ),
                "federated_search_service": (StubSearchService()),
            },
        )(),
    )


@pytest.mark.asyncio
async def test_server_registers_search_papers_tool() -> None:
    """The server should expose the federated paper search tool."""

    server = create_mcp_server(build_server_dependencies())

    tools = await server.list_tools()

    tool_names = {tool.name for tool in tools}

    assert "health_check" in tool_names
    assert "search_papers" in tool_names


@pytest.mark.asyncio
async def test_search_papers_has_input_and_output_schemas() -> None:
    """The search tool should expose structured protocol schemas."""

    server = create_mcp_server(build_server_dependencies())

    tools = await server.list_tools()

    search_tool = next(tool for tool in tools if tool.name == "search_papers")

    assert search_tool.description is not None
    assert "Semantic Scholar" in (search_tool.description)
    assert "arXiv" in search_tool.description

    assert search_tool.inputSchema["type"] == "object"

    properties = search_tool.inputSchema["properties"]

    assert "query" in properties
    assert "providers" in properties
    assert "limit" in properties
    assert "year_from" in properties
    assert "fields_of_study" in properties

    assert search_tool.outputSchema is not None
