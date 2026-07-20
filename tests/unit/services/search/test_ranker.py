"""Tests for deterministic federated-result ranking."""

from __future__ import annotations

from tests.unit.services.search.helpers import build_paper

from research_intelligence_mcp.domain.enums import ProviderName
from research_intelligence_mcp.services.search.ranker import (
    ResultRanker,
)


def test_ranks_higher_citation_count_first() -> None:
    """Citation count should be the primary ranking key."""

    lower = build_paper(
        title="Lower Citations",
        source=ProviderName.ARXIV,
        arxiv_id="2401.00001",
        citation_count=10,
    )
    higher = build_paper(
        title="Higher Citations",
        source=ProviderName.SEMANTIC_SCHOLAR,
        corpus_id=2,
        citation_count=100,
    )

    ranked = ResultRanker().rank(
        (
            lower,
            higher,
        )
    )

    assert ranked == (
        higher,
        lower,
    )


def test_uses_year_as_secondary_ranking_key() -> None:
    """Newer papers should win citation-count ties."""

    older = build_paper(
        title="Older Paper",
        source=ProviderName.ARXIV,
        arxiv_id="2301.00001",
        year=2023,
        citation_count=10,
    )
    newer = build_paper(
        title="Newer Paper",
        source=ProviderName.SEMANTIC_SCHOLAR,
        corpus_id=2,
        year=2025,
        citation_count=10,
    )

    ranked = ResultRanker().rank(
        (
            older,
            newer,
        )
    )

    assert ranked == (
        newer,
        older,
    )


def test_uses_title_as_stable_final_tiebreaker() -> None:
    """Title should make ordering deterministic when metadata ties."""

    beta = build_paper(
        title="Beta Paper",
        source=ProviderName.ARXIV,
        arxiv_id="2401.00001",
        year=2024,
        citation_count=10,
    )
    alpha = build_paper(
        title="Alpha Paper",
        source=ProviderName.SEMANTIC_SCHOLAR,
        corpus_id=2,
        year=2024,
        citation_count=10,
    )

    ranked = ResultRanker().rank(
        (
            beta,
            alpha,
        )
    )

    assert ranked == (
        alpha,
        beta,
    )


def test_handles_missing_optional_ranking_metadata() -> None:
    """Missing citations and year should be treated as zero."""

    unknown = build_paper(
        title="Unknown Metadata",
        source=ProviderName.ARXIV,
        arxiv_id="2401.00001",
        year=None,
        citation_count=None,
    )
    known = build_paper(
        title="Known Metadata",
        source=ProviderName.SEMANTIC_SCHOLAR,
        corpus_id=2,
        year=2024,
        citation_count=1,
    )

    ranked = ResultRanker().rank(
        (
            unknown,
            known,
        )
    )

    assert ranked == (
        known,
        unknown,
    )


def test_produces_same_order_for_repeated_calls() -> None:
    """Ranking must remain deterministic."""

    papers = (
        build_paper(
            title="Charlie",
            source=ProviderName.ARXIV,
            arxiv_id="2401.00001",
            citation_count=5,
        ),
        build_paper(
            title="Alpha",
            source=ProviderName.SEMANTIC_SCHOLAR,
            corpus_id=2,
            citation_count=5,
        ),
        build_paper(
            title="Bravo",
            source=ProviderName.ARXIV,
            arxiv_id="2401.00003",
            citation_count=5,
        ),
    )

    ranker = ResultRanker()

    assert ranker.rank(papers) == ranker.rank(papers)
