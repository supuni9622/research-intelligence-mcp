"""Tests for academic paper search MCP tool behavior."""

from __future__ import annotations

from typing import cast

import pytest

from research_intelligence_mcp.config.settings import (
    Settings,
)
from research_intelligence_mcp.domain.enums import (
    ProviderName,
)
from research_intelligence_mcp.domain.requests import (
    PaginationMetadata,
    SearchRequest,
    SearchResult,
)
from research_intelligence_mcp.mcp.dependencies import (
    AppDependencies,
)
from research_intelligence_mcp.mcp.schemas.search import (
    SearchPapersInput,
)
from research_intelligence_mcp.mcp.tools.search import (
    execute_search_papers,
)


class StubFederatedSearchService:
    """Record federated search requests and return a fixed result."""

    def __init__(
        self,
        *,
        result: SearchResult,
    ) -> None:
        """Initialize the service stub."""

        self.result = result
        self.requests: list[SearchRequest] = []

    async def search(
        self,
        request: SearchRequest,
    ) -> SearchResult:
        """Record and return the configured result."""

        self.requests.append(request)

        return self.result


def build_empty_result(
    *,
    query: str,
    providers: tuple[ProviderName, ...],
) -> SearchResult:
    """Build a successful empty canonical result."""

    return SearchResult(
        query=query,
        papers=(),
        pagination=PaginationMetadata(
            offset=0,
            limit=10,
            returned=0,
            total=0,
            has_more=False,
        ),
        providers_requested=providers,
        providers_succeeded=providers,
        failures=(),
        warnings=(),
    )


def build_dependencies_with_search_service(
    service: StubFederatedSearchService,
) -> AppDependencies:
    """Build a minimal typed dependency stand-in for the tool test."""

    return cast(
        AppDependencies,
        type(
            "ToolDependencies",
            (),
            {
                "settings": Settings(
                    _env_file=None,
                    APP_ENVIRONMENT="test",
                ),
                "federated_search_service": service,
            },
        )(),
    )


@pytest.mark.asyncio
async def test_executes_federated_search_service() -> None:
    """The MCP behavior should call the federated service once."""

    providers = (
        ProviderName.SEMANTIC_SCHOLAR,
        ProviderName.ARXIV,
    )

    expected_result = build_empty_result(
        query="retrieval augmented generation",
        providers=providers,
    )

    service = StubFederatedSearchService(result=expected_result)

    dependencies = build_dependencies_with_search_service(service)

    search_input = SearchPapersInput(
        query="retrieval augmented generation",
        providers=providers,
    )

    result = await execute_search_papers(
        search_input=search_input,
        dependencies=dependencies,
    )

    assert result is expected_result
    assert len(service.requests) == 1

    request = service.requests[0]

    assert request.query == ("retrieval augmented generation")
    assert request.providers == providers


@pytest.mark.asyncio
async def test_preserves_all_search_filters() -> None:
    """All validated MCP fields should reach the service layer."""

    expected_result = build_empty_result(
        query="agentic retrieval",
        providers=(ProviderName.ARXIV,),
    )

    service = StubFederatedSearchService(result=expected_result)

    dependencies = build_dependencies_with_search_service(service)

    search_input = SearchPapersInput(
        query="agentic retrieval",
        providers=(ProviderName.ARXIV,),
        limit=10,
        offset=0,
        year_from=2022,
        year_to=2026,
        fields_of_study=(
            "cs.IR",
            "cs.AI",
        ),
        open_access_only=True,
    )

    await execute_search_papers(
        search_input=search_input,
        dependencies=dependencies,
    )

    request = service.requests[0]

    assert request.year_from == 2022
    assert request.year_to == 2026
    assert request.fields_of_study == (
        "cs.IR",
        "cs.AI",
    )
    assert request.open_access_only is True
