"""Tests for MCP server construction and tool registration."""

from __future__ import annotations

from typing import cast

import pytest

from research_intelligence_mcp.config.settings import (
    Settings,
)
from research_intelligence_mcp.domain.enums import (
    ProviderName,
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


class StubProviderRegistry:
    """Unused provider registry stand-in for registration tests."""

    def get(
        self,
        provider_name: ProviderName,
    ) -> object:
        """Fail if unexpectedly used."""

        raise AssertionError(
            "Provider resolution should not execute during registration."
        )


def build_server_dependencies(
    settings: Settings | None = None,
) -> AppDependencies:
    """Build minimal dependencies required during server creation."""

    return cast(
        AppDependencies,
        type(
            "ServerDependencies",
            (),
            {
                "settings": settings
                or Settings(
                    _env_file=None,
                    APP_ENVIRONMENT="test",
                ),
                "federated_search_service": StubSearchService(),
                "provider_registry": StubProviderRegistry(),
            },
        )(),
    )


@pytest.mark.asyncio
async def test_server_registers_expected_tools() -> None:
    """The server should expose all implemented MCP tools."""

    server = create_mcp_server(build_server_dependencies())

    tools = await server.list_tools()

    tool_names = {tool.name for tool in tools}

    assert tool_names == {
        "health_check",
        "search_papers",
        "get_paper",
        "get_paper_citations",
        "get_paper_references",
        "get_related_papers",
        "resolve_paper_access",
    }


@pytest.mark.asyncio
async def test_search_papers_has_input_and_output_schemas() -> None:
    """The search tool should expose structured protocol schemas."""

    server = create_mcp_server(build_server_dependencies())

    tools = await server.list_tools()

    search_tool = next(tool for tool in tools if tool.name == "search_papers")

    assert search_tool.description is not None
    assert "Semantic Scholar" in search_tool.description
    assert "arXiv" in search_tool.description

    assert search_tool.inputSchema["type"] == "object"

    properties = search_tool.inputSchema["properties"]

    assert "query" in properties
    assert "providers" in properties
    assert "limit" in properties
    assert "offset" in properties
    assert "year_from" in properties
    assert "year_to" in properties
    assert "fields_of_study" in properties
    assert "open_access_only" in properties
    assert "sort" in properties

    assert search_tool.outputSchema is not None


@pytest.mark.asyncio
async def test_get_paper_has_input_and_output_schemas() -> None:
    """The get-paper tool should expose structured protocol schemas."""

    server = create_mcp_server(build_server_dependencies())

    tools = await server.list_tools()

    paper_tool = next(tool for tool in tools if tool.name == "get_paper")

    assert paper_tool.description is not None
    assert "single academic paper" in paper_tool.description
    assert "provider-neutral" in paper_tool.description

    assert paper_tool.inputSchema["type"] == "object"

    properties = paper_tool.inputSchema["properties"]

    assert "provider" in properties
    assert "paper_id" in properties

    required_fields = set(
        paper_tool.inputSchema.get(
            "required",
            [],
        )
    )

    assert "provider" in required_fields
    assert "paper_id" in required_fields

    assert paper_tool.outputSchema is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_name",
    [
        "get_paper_citations",
        "get_paper_references",
    ],
)
async def test_paper_graph_tools_have_structured_schemas(
    tool_name: str,
) -> None:
    """Citation and reference tools should expose graph input schemas."""

    server = create_mcp_server(build_server_dependencies())

    tools = await server.list_tools()

    graph_tool = next(tool for tool in tools if tool.name == tool_name)

    assert graph_tool.description is not None
    assert "Semantic Scholar" in graph_tool.description
    assert "arXiv" in graph_tool.description

    assert graph_tool.inputSchema["type"] == "object"

    properties = graph_tool.inputSchema["properties"]

    assert "provider" in properties
    assert "paper_id" in properties
    assert "limit" in properties
    assert "offset" in properties

    required_fields = set(
        graph_tool.inputSchema.get(
            "required",
            [],
        )
    )

    assert "provider" in required_fields
    assert "paper_id" in required_fields
    assert "limit" not in required_fields
    assert "offset" not in required_fields

    assert graph_tool.outputSchema is not None


@pytest.mark.asyncio
async def test_get_related_papers_has_structured_schema() -> None:
    """The related-paper tool should expose recommendation inputs."""

    server = create_mcp_server(build_server_dependencies())

    tools = await server.list_tools()

    related_tool = next(tool for tool in tools if tool.name == "get_related_papers")

    assert related_tool.description is not None
    assert "recommendation" in related_tool.description
    assert "Semantic Scholar" in related_tool.description

    assert related_tool.inputSchema["type"] == "object"

    properties = related_tool.inputSchema["properties"]

    assert "provider" in properties
    assert "paper_id" in properties
    assert "limit" in properties
    assert "negative_paper_ids" in properties

    required_fields = set(
        related_tool.inputSchema.get(
            "required",
            [],
        )
    )

    assert "provider" in required_fields
    assert "paper_id" in required_fields
    assert "limit" not in required_fields
    assert "negative_paper_ids" not in required_fields

    assert related_tool.outputSchema is not None


@pytest.mark.asyncio
async def test_resolve_paper_access_has_structured_schema() -> None:
    """The access tool should expose paper resolution inputs."""

    server = create_mcp_server(build_server_dependencies())

    tools = await server.list_tools()

    access_tool = next(tool for tool in tools if tool.name == "resolve_paper_access")

    assert access_tool.description is not None
    assert "access" in access_tool.description
    assert "PDF" in access_tool.description

    assert access_tool.inputSchema["type"] == "object"

    properties = access_tool.inputSchema["properties"]

    assert "provider" in properties
    assert "paper_id" in properties

    required_fields = set(
        access_tool.inputSchema.get(
            "required",
            [],
        )
    )

    assert "provider" in required_fields
    assert "paper_id" in required_fields

    assert access_tool.outputSchema is not None


def test_auth_disabled_by_default_leaves_server_unauthenticated() -> None:
    """Backward compatibility: no auth settings means no token verifier."""

    server = create_mcp_server(build_server_dependencies())

    assert server._token_verifier is None
    assert server.settings.auth is None


def test_auth_enabled_wires_token_verifier_and_required_scopes() -> None:
    """Enabling auth should attach a token verifier and required scopes."""

    settings = Settings(
        _env_file=None,
        APP_ENVIRONMENT="test",
        AUTH_ENABLED=True,
        AUTH_ISSUER="https://auth.researchmind.ai",
        AUTH_AUDIENCE="research-intelligence-mcp",
        AUTH_JWT_ALGORITHMS="HS256",
        AUTH_JWT_SECRET="a-sufficiently-long-shared-secret",
        AUTH_REQUIRED_SCOPES="research-intelligence/invoke",
    )

    server = create_mcp_server(build_server_dependencies(settings))

    assert server._token_verifier is not None
    assert server.settings.auth is not None
    assert server.settings.auth.required_scopes == ["research-intelligence/invoke"]
    assert str(server.settings.auth.issuer_url) == "https://auth.researchmind.ai/"


@pytest.mark.asyncio
async def test_server_still_registers_tools_when_auth_is_enabled() -> None:
    """Enabling auth must not affect tool registration."""

    settings = Settings(
        _env_file=None,
        APP_ENVIRONMENT="test",
        AUTH_ENABLED=True,
        AUTH_ISSUER="https://auth.researchmind.ai",
        AUTH_AUDIENCE="research-intelligence-mcp",
        AUTH_JWT_ALGORITHMS="HS256",
        AUTH_JWT_SECRET="a-sufficiently-long-shared-secret",
    )

    server = create_mcp_server(build_server_dependencies(settings))

    tools = await server.list_tools()
    tool_names = {tool.name for tool in tools}

    assert "health_check" in tool_names
    assert "search_papers" in tool_names
