"""Tests for paper-related MCP tool execution."""

from __future__ import annotations

from typing import cast

import pytest

from research_intelligence_mcp.domain.enums import (
    AccessStatus,
    PaperRelationType,
    ProviderName,
)
from research_intelligence_mcp.domain.identifiers import (
    PaperIdentifiers,
)
from research_intelligence_mcp.domain.models import (
    Paper,
    PaperAccess,
    PaperReference,
)
from research_intelligence_mcp.mcp.dependencies import (
    AppDependencies,
)
from research_intelligence_mcp.mcp.schemas.paper import (
    GetPaperInput,
    GetRelatedPapersInput,
    PaperGraphInput,
)
from research_intelligence_mcp.mcp.tools.paper import (
    execute_get_paper,
    execute_get_paper_citations,
    execute_get_paper_references,
    execute_get_related_papers,
    execute_resolve_paper_access,
)


def build_paper(
    *,
    paper_id: str,
    title: str,
) -> Paper:
    """Build one canonical Semantic Scholar paper."""

    return Paper(
        identifiers=PaperIdentifiers(
            semantic_scholar_id=paper_id,
        ),
        title=title,
        access=PaperAccess(
            status=AccessStatus.OPEN_ACCESS,
            landing_page_url=(
                f"https://www.semanticscholar.org/paper/{paper_id}"
            ),
            pdf_url=f"https://example.org/{paper_id}.pdf",
            license="CC BY 4.0",
            repository=ProviderName.SEMANTIC_SCHOLAR,
        ),
        sources=(
            ProviderName.SEMANTIC_SCHOLAR,
        ),
    )


class StubProvider:
    """Paper provider stand-in for MCP execution tests."""

    name = ProviderName.SEMANTIC_SCHOLAR

    def __init__(self) -> None:
        self.last_paper_id: str | None = None
        self.last_limit: int | None = None
        self.last_offset: int | None = None
        self.last_negative_paper_ids: list[str] | None = None

    async def get_paper(
        self,
        paper_id: str,
    ) -> Paper:
        """Return one canonical paper."""

        self.last_paper_id = paper_id

        return build_paper(
            paper_id="204e3073870fae3d05bcbc2f6a8e263d9b72e776",
            title="Attention Is All You Need",
        )

    async def get_citations(
        self,
        paper_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PaperReference]:
        """Return one citation relationship."""

        self.last_paper_id = paper_id
        self.last_limit = limit
        self.last_offset = offset

        return [
            PaperReference(
                relation=PaperRelationType.CITATION,
                paper=build_paper(
                    paper_id="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    title="A Paper Citing the Transformer",
                ),
                contexts=(
                    "The Transformer architecture introduced self-attention.",
                ),
                intents=(
                    "background",
                ),
                is_influential=True,
            )
        ]

    async def get_references(
        self,
        paper_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PaperReference]:
        """Return one reference relationship."""

        self.last_paper_id = paper_id
        self.last_limit = limit
        self.last_offset = offset

        return [
            PaperReference(
                relation=PaperRelationType.REFERENCE,
                paper=build_paper(
                    paper_id="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                    title="Neural Machine Translation by Jointly Learning",
                ),
                contexts=(
                    "The work builds on attention-based sequence models.",
                ),
                intents=(
                    "background",
                ),
                is_influential=False,
            )
        ]

    async def get_related_papers(
        self,
        paper_id: str,
        *,
        limit: int = 10,
        negative_paper_ids: list[str] | None = None,
    ) -> list[Paper]:
        """Return one related paper."""

        self.last_paper_id = paper_id
        self.last_limit = limit
        self.last_negative_paper_ids = negative_paper_ids

        return [
            build_paper(
                paper_id="cccccccccccccccccccccccccccccccccccccccc",
                title="BERT: Pre-training of Deep Bidirectional Transformers",
            )
        ]


class StubRegistry:
    """Provider registry stand-in."""

    def __init__(
        self,
        provider: StubProvider,
    ) -> None:
        self.provider = provider
        self.requested_provider: ProviderName | None = None

    def get(
        self,
        provider_name: ProviderName,
    ) -> StubProvider:
        """Return the configured stub provider."""

        self.requested_provider = provider_name

        return self.provider


class StubDependencies:
    """Minimal dependency object used by paper tool tests."""

    def __init__(
        self,
        provider: StubProvider,
    ) -> None:
        self.provider_registry = StubRegistry(provider)


def build_dependencies(
    provider: StubProvider,
) -> AppDependencies:
    """Build typed stub application dependencies."""

    return cast(
        AppDependencies,
        StubDependencies(provider),
    )


@pytest.mark.asyncio
async def test_execute_get_paper() -> None:
    """get_paper should resolve and execute the selected provider."""

    provider = StubProvider()
    dependencies = build_dependencies(provider)

    result = await execute_get_paper(
        paper_input=GetPaperInput(
            provider=ProviderName.SEMANTIC_SCHOLAR,
            paper_id="DOI:10.48550/arXiv.1706.03762",
        ),
        dependencies=dependencies,
    )

    assert result.title == "Attention Is All You Need"
    assert provider.last_paper_id == "DOI:10.48550/arXiv.1706.03762"


@pytest.mark.asyncio
async def test_execute_get_paper_citations() -> None:
    """Citation execution should preserve pagination and relationships."""

    provider = StubProvider()
    dependencies = build_dependencies(provider)

    result = await execute_get_paper_citations(
        paper_input=PaperGraphInput(
            provider=ProviderName.SEMANTIC_SCHOLAR,
            paper_id="DOI:10.48550/arXiv.1706.03762",
            limit=25,
            offset=10,
        ),
        dependencies=dependencies,
    )

    assert result.provider == ProviderName.SEMANTIC_SCHOLAR
    assert result.paper_id == "DOI:10.48550/arXiv.1706.03762"
    assert result.limit == 25
    assert result.offset == 10
    assert result.returned == 1

    assert len(result.references) == 1
    assert (
        result.references[0].relation
        == PaperRelationType.CITATION
    )

    assert provider.last_limit == 25
    assert provider.last_offset == 10


@pytest.mark.asyncio
async def test_execute_get_paper_references() -> None:
    """Reference execution should preserve pagination and relationships."""

    provider = StubProvider()
    dependencies = build_dependencies(provider)

    result = await execute_get_paper_references(
        paper_input=PaperGraphInput(
            provider=ProviderName.SEMANTIC_SCHOLAR,
            paper_id="DOI:10.48550/arXiv.1706.03762",
            limit=30,
            offset=5,
        ),
        dependencies=dependencies,
    )

    assert result.returned == 1
    assert len(result.references) == 1

    assert (
        result.references[0].relation
        == PaperRelationType.REFERENCE
    )

    assert provider.last_limit == 30
    assert provider.last_offset == 5


@pytest.mark.asyncio
async def test_execute_get_related_papers() -> None:
    """Related-paper execution should forward positive and negative seeds."""

    provider = StubProvider()
    dependencies = build_dependencies(provider)

    result = await execute_get_related_papers(
        paper_input=GetRelatedPapersInput(
            provider=ProviderName.SEMANTIC_SCHOLAR,
            paper_id="DOI:10.48550/arXiv.1706.03762",
            limit=8,
            negative_paper_ids=(
                "negative-paper-one",
                "negative-paper-two",
            ),
        ),
        dependencies=dependencies,
    )

    assert result.provider == ProviderName.SEMANTIC_SCHOLAR
    assert result.limit == 8
    assert result.returned == 1

    assert result.negative_paper_ids == (
        "negative-paper-one",
        "negative-paper-two",
    )

    assert result.papers[0].title.startswith("BERT")

    assert provider.last_paper_id == (
        "DOI:10.48550/arXiv.1706.03762"
    )

    assert provider.last_negative_paper_ids == [
        "negative-paper-one",
        "negative-paper-two",
    ]


@pytest.mark.asyncio
async def test_execute_get_related_papers_passes_none_without_negative_ids() -> None:
    """Empty negative seeds should be forwarded as None."""

    provider = StubProvider()
    dependencies = build_dependencies(provider)

    await execute_get_related_papers(
        paper_input=GetRelatedPapersInput(
            provider=ProviderName.SEMANTIC_SCHOLAR,
            paper_id="DOI:10.48550/arXiv.1706.03762",
        ),
        dependencies=dependencies,
    )

    assert provider.last_negative_paper_ids is None


@pytest.mark.asyncio
async def test_execute_resolve_paper_access() -> None:
    """Access resolution should return canonical paper access metadata."""

    provider = StubProvider()
    dependencies = build_dependencies(provider)

    result = await execute_resolve_paper_access(
        paper_input=GetPaperInput(
            provider=ProviderName.SEMANTIC_SCHOLAR,
            paper_id="DOI:10.48550/arXiv.1706.03762",
        ),
        dependencies=dependencies,
    )

    assert result.provider == ProviderName.SEMANTIC_SCHOLAR
    assert result.title == "Attention Is All You Need"

    assert result.identifiers == (
        "semantic_scholar:"
        "204e3073870fae3d05bcbc2f6a8e263d9b72e776"
    )

    assert result.access.status == AccessStatus.OPEN_ACCESS
    assert result.access.pdf_url is not None
    assert result.access.license == "CC BY 4.0"