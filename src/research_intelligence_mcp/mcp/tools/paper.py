from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from research_intelligence_mcp.domain.enums import (
    ProviderName,
)
from research_intelligence_mcp.domain.models import (
    Paper,
)
from research_intelligence_mcp.mcp.dependencies import (
    AppDependencies,
)
from research_intelligence_mcp.mcp.schemas.paper import (
    GetPaperInput,
)

_GET_PAPER_DESCRIPTION = """
Retrieve metadata for a single academic paper.

Supported identifiers include:

- DOI
- arXiv id
- Semantic Scholar id
- Corpus id (provider dependent)

Returns canonical provider-neutral paper metadata.

This tool does not summarize papers.
""".strip()


async def execute_get_paper(
    *,
    paper_input: GetPaperInput,
    dependencies: AppDependencies,
) -> Paper:
    provider = dependencies.provider_registry.get(
        paper_input.provider,
    )

    return await provider.get_paper(
        paper_input.paper_id,
    )


def register_paper_tools(
    *,
    server: FastMCP,
    dependencies: AppDependencies,
) -> None:
    @server.tool(
        name="get_paper",
        description=_GET_PAPER_DESCRIPTION,
    )
    async def get_paper(
        provider: ProviderName,
        paper_id: str,
    ) -> Paper:
        paper_input = GetPaperInput(
            provider=provider,
            paper_id=paper_id,
        )

        return await execute_get_paper(
            paper_input=paper_input,
            dependencies=dependencies,
        )