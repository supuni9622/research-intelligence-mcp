"""MCP tools for paper metadata, graph traversal, and access resolution."""

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
    GetRelatedPapersInput,
    PaperAccessResult,
    PaperGraphInput,
    PaperReferencesResult,
    RelatedPapersResult,
)

_GET_PAPER_DESCRIPTION = """
Retrieve canonical metadata for a single academic paper.

Supported identifiers depend on the selected provider and may include:

- DOI;
- arXiv identifier;
- Semantic Scholar paper identifier;
- Semantic Scholar CorpusId;
- PubMed identifier.

Use arXiv for direct arXiv metadata retrieval. Use Semantic Scholar when richer
citation counts, reference counts, publication metadata, and external
identifiers are required.

This tool returns provider-neutral structured metadata. It does not summarize
the paper or read the full paper content.
""".strip()


_GET_PAPER_CITATIONS_DESCRIPTION = """
Retrieve papers that cite a specified academic paper.

This tool traverses the citation graph from an origin paper to papers that cite
it. Each returned relationship may include:

- canonical citing-paper metadata;
- citation contexts;
- citation intent labels;
- influential-citation status.

Semantic Scholar supports citation graph retrieval. arXiv does not expose a
citation graph API and will return a normalized unsupported-operation error.

This tool retrieves structured graph metadata only. It does not synthesize or
summarize the citing papers.
""".strip()


_GET_PAPER_REFERENCES_DESCRIPTION = """
Retrieve papers referenced by a specified academic paper.

This tool traverses the reference graph from an origin paper to papers listed
in its bibliography. Each returned relationship may include:

- canonical referenced-paper metadata;
- reference contexts;
- intent labels;
- influential-reference status.

Semantic Scholar supports reference graph retrieval. arXiv does not expose a
reference graph API and will return a normalized unsupported-operation error.

This tool retrieves structured graph metadata only. It does not evaluate the
quality of the references.
""".strip()


_GET_RELATED_PAPERS_DESCRIPTION = """
Retrieve papers related to a specified academic paper.

The selected paper is used as a positive recommendation seed. Optional negative
paper identifiers can be supplied to reduce recommendations similar to those
papers.

Semantic Scholar supports related-paper recommendations. arXiv does not expose
a related-paper recommendation API and will return a normalized unsupported
operation error.

This tool returns canonical paper records. It does not explain why each paper
was recommended.
""".strip()


_RESOLVE_PAPER_ACCESS_DESCRIPTION = """
Resolve known access information for an academic paper.

The tool retrieves the paper through the selected provider and returns its
canonical access metadata, including:

- open, closed, or unknown access status;
- landing-page URL;
- direct PDF URL when available;
- known license;
- repository or provider hosting the accessible copy.

This tool resolves metadata only. It does not download, parse, or return the
paper PDF.
""".strip()


async def execute_get_paper(
    *,
    paper_input: GetPaperInput,
    dependencies: AppDependencies,
) -> Paper:
    """Retrieve one canonical paper through the selected provider."""

    provider = dependencies.provider_registry.get(
        paper_input.provider,
    )

    return await provider.get_paper(
        paper_input.paper_id,
    )


async def execute_get_paper_citations(
    *,
    paper_input: PaperGraphInput,
    dependencies: AppDependencies,
) -> PaperReferencesResult:
    """Retrieve papers citing the requested paper."""

    provider = dependencies.provider_registry.get(
        paper_input.provider,
    )

    references = await provider.get_citations(
        paper_input.paper_id,
        limit=paper_input.limit,
        offset=paper_input.offset,
    )

    normalized_references = tuple(references)

    return PaperReferencesResult(
        provider=paper_input.provider,
        paper_id=paper_input.paper_id,
        offset=paper_input.offset,
        limit=paper_input.limit,
        returned=len(normalized_references),
        references=normalized_references,
    )


async def execute_get_paper_references(
    *,
    paper_input: PaperGraphInput,
    dependencies: AppDependencies,
) -> PaperReferencesResult:
    """Retrieve papers referenced by the requested paper."""

    provider = dependencies.provider_registry.get(
        paper_input.provider,
    )

    references = await provider.get_references(
        paper_input.paper_id,
        limit=paper_input.limit,
        offset=paper_input.offset,
    )

    normalized_references = tuple(references)

    return PaperReferencesResult(
        provider=paper_input.provider,
        paper_id=paper_input.paper_id,
        offset=paper_input.offset,
        limit=paper_input.limit,
        returned=len(normalized_references),
        references=normalized_references,
    )


async def execute_get_related_papers(
    *,
    paper_input: GetRelatedPapersInput,
    dependencies: AppDependencies,
) -> RelatedPapersResult:
    """Retrieve papers related to the requested positive seed paper."""

    provider = dependencies.provider_registry.get(
        paper_input.provider,
    )

    negative_paper_ids = (
        list(paper_input.negative_paper_ids) if paper_input.negative_paper_ids else None
    )

    papers = await provider.get_related_papers(
        paper_input.paper_id,
        limit=paper_input.limit,
        negative_paper_ids=negative_paper_ids,
    )

    normalized_papers = tuple(papers)

    return RelatedPapersResult(
        provider=paper_input.provider,
        paper_id=paper_input.paper_id,
        limit=paper_input.limit,
        returned=len(normalized_papers),
        negative_paper_ids=paper_input.negative_paper_ids,
        papers=normalized_papers,
    )


async def execute_resolve_paper_access(
    *,
    paper_input: GetPaperInput,
    dependencies: AppDependencies,
) -> PaperAccessResult:
    """Resolve canonical paper access metadata."""

    paper = await execute_get_paper(
        paper_input=paper_input,
        dependencies=dependencies,
    )

    return PaperAccessResult(
        provider=paper_input.provider,
        paper_id=paper_input.paper_id,
        identifiers=paper.identifiers.preferred_identifier(),
        title=paper.title,
        access=paper.access,
    )


def register_paper_tools(
    *,
    server: FastMCP,
    dependencies: AppDependencies,
) -> None:
    """Register paper metadata and graph tools with the MCP server."""

    @server.tool(
        name="get_paper",
        description=_GET_PAPER_DESCRIPTION,
    )
    async def get_paper(
        provider: ProviderName,
        paper_id: str,
    ) -> Paper:
        """Retrieve one academic paper.

        Args:
            provider:
                Provider used to retrieve the paper.
            paper_id:
                Provider-supported paper identifier.

        Returns:
            Canonical provider-neutral paper metadata.
        """

        paper_input = GetPaperInput(
            provider=provider,
            paper_id=paper_id,
        )

        return await execute_get_paper(
            paper_input=paper_input,
            dependencies=dependencies,
        )

    @server.tool(
        name="get_paper_citations",
        description=_GET_PAPER_CITATIONS_DESCRIPTION,
    )
    async def get_paper_citations(
        provider: ProviderName,
        paper_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> PaperReferencesResult:
        """Retrieve papers that cite an academic paper.

        Args:
            provider:
                Provider used for citation graph retrieval.
            paper_id:
                Identifier of the paper whose citations should be retrieved.
            limit:
                Maximum number of citation relationships to return.
            offset:
                Zero-based citation result offset.

        Returns:
            Structured canonical citation relationships.
        """

        paper_input = PaperGraphInput(
            provider=provider,
            paper_id=paper_id,
            limit=limit,
            offset=offset,
        )

        return await execute_get_paper_citations(
            paper_input=paper_input,
            dependencies=dependencies,
        )

    @server.tool(
        name="get_paper_references",
        description=_GET_PAPER_REFERENCES_DESCRIPTION,
    )
    async def get_paper_references(
        provider: ProviderName,
        paper_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> PaperReferencesResult:
        """Retrieve papers referenced by an academic paper.

        Args:
            provider:
                Provider used for reference graph retrieval.
            paper_id:
                Identifier of the paper whose references should be retrieved.
            limit:
                Maximum number of reference relationships to return.
            offset:
                Zero-based reference result offset.

        Returns:
            Structured canonical reference relationships.
        """

        paper_input = PaperGraphInput(
            provider=provider,
            paper_id=paper_id,
            limit=limit,
            offset=offset,
        )

        return await execute_get_paper_references(
            paper_input=paper_input,
            dependencies=dependencies,
        )

    @server.tool(
        name="get_related_papers",
        description=_GET_RELATED_PAPERS_DESCRIPTION,
    )
    async def get_related_papers(
        provider: ProviderName,
        paper_id: str,
        limit: int = 10,
        negative_paper_ids: tuple[str, ...] = (),
    ) -> RelatedPapersResult:
        """Retrieve papers related to an academic paper.

        Args:
            provider:
                Provider used for related-paper discovery.
            paper_id:
                Positive seed paper identifier.
            limit:
                Maximum number of related papers to return.
            negative_paper_ids:
                Optional negative recommendation seed identifiers.

        Returns:
            Structured canonical related-paper recommendations.
        """

        paper_input = GetRelatedPapersInput(
            provider=provider,
            paper_id=paper_id,
            limit=limit,
            negative_paper_ids=negative_paper_ids,
        )

        return await execute_get_related_papers(
            paper_input=paper_input,
            dependencies=dependencies,
        )

    @server.tool(
        name="resolve_paper_access",
        description=_RESOLVE_PAPER_ACCESS_DESCRIPTION,
    )
    async def resolve_paper_access(
        provider: ProviderName,
        paper_id: str,
    ) -> PaperAccessResult:
        """Resolve known paper access metadata.

        Args:
            provider:
                Provider used to resolve the paper.
            paper_id:
                Provider-supported paper identifier.

        Returns:
            Canonical access status, URLs, license, and repository metadata.
        """

        paper_input = GetPaperInput(
            provider=provider,
            paper_id=paper_id,
        )

        return await execute_resolve_paper_access(
            paper_input=paper_input,
            dependencies=dependencies,
        )
