"""MCP tools for academic paper discovery."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from research_intelligence_mcp.domain.enums import (
    ProviderName,
    SearchSort,
)
from research_intelligence_mcp.domain.requests import (
    SearchResult,
)
from research_intelligence_mcp.mcp.dependencies import (
    AppDependencies,
)
from research_intelligence_mcp.mcp.observability import (
    correlation_scope,
)
from research_intelligence_mcp.mcp.schemas.search import (
    SearchPapersInput,
)

_SEARCH_PAPERS_DESCRIPTION = """
Search for academic papers across Semantic Scholar, arXiv, or both providers.

Use this tool when the user wants to:

- discover papers about a research topic;
- find literature related to a research question;
- search for a known paper title;
- find papers by keywords or an author name;
- restrict results by publication year;
- restrict results by academic field or arXiv category;
- request papers with known open-access metadata;
- compare results from Semantic Scholar and arXiv.

The tool executes selected providers concurrently, preserves successful results
when another provider fails, merges duplicate papers, preserves provider
provenance, and returns deterministic provider-neutral paper records.

The response includes:

- canonical paper metadata;
- normalized paper identifiers;
- author and publication metadata;
- known access URLs;
- provider attribution;
- pagination metadata;
- non-fatal warnings;
- normalized partial-provider failures.

This tool performs academic paper discovery only. It does not summarize papers,
answer research questions, synthesize evidence, or generate research reports.
""".strip()


async def execute_search_papers(
    *,
    search_input: SearchPapersInput,
    dependencies: AppDependencies,
) -> SearchResult:
    """Execute validated federated academic paper search.

    This function contains the testable application-facing tool behavior.
    FastMCP registration is kept separately in ``register_search_tools``.
    """

    request = search_input.to_domain_request()

    return await dependencies.federated_search_service.search(request)


def register_search_tools(
    *,
    server: FastMCP,
    dependencies: AppDependencies,
) -> None:
    """Register academic paper search tools with the MCP server."""

    @server.tool(
        name="search_papers",
        description=_SEARCH_PAPERS_DESCRIPTION,
    )
    async def search_papers(
        ctx: Context[Any, Any, Any],
        query: str,
        providers: tuple[ProviderName, ...] = (
            ProviderName.SEMANTIC_SCHOLAR,
            ProviderName.ARXIV,
        ),
        limit: int = 10,
        offset: int = 0,
        year_from: int | None = None,
        year_to: int | None = None,
        fields_of_study: tuple[str, ...] = (),
        open_access_only: bool = False,
        sort: SearchSort = SearchSort.RELEVANCE,
    ) -> SearchResult:
        """Search academic papers across one or more research providers.

        Args:
            query:
                Natural-language research topic, title, author, or keywords.
            providers:
                Providers to query. Defaults to Semantic Scholar and arXiv.
            limit:
                Maximum number of final deduplicated papers to return.
            offset:
                Zero-based result offset for provider pagination.
            year_from:
                Optional inclusive earliest publication year.
            year_to:
                Optional inclusive latest publication year.
            fields_of_study:
                Optional academic subjects or arXiv category filters.
            open_access_only:
                Whether to request papers with known open-access metadata.
            sort:
                Requested result ordering.

        Returns:
            A provider-neutral structured search result containing canonical
            papers, pagination, provider outcomes, warnings, and failures.
        """

        with correlation_scope(ctx):
            search_input = SearchPapersInput(
                query=query,
                providers=providers,
                limit=limit,
                offset=offset,
                year_from=year_from,
                year_to=year_to,
                fields_of_study=fields_of_study,
                open_access_only=open_access_only,
                sort=sort,
            )

            return await execute_search_papers(
                search_input=search_input,
                dependencies=dependencies,
            )
