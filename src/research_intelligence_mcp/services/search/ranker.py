"""Deterministic ranking for federated search results."""

from __future__ import annotations

from datetime import date

from research_intelligence_mcp.domain.models import Paper


class ResultRanker:
    """Apply stable deterministic ordering to papers."""

    def rank(
        self,
        papers: tuple[Paper, ...],
    ) -> tuple[Paper, ...]:
        """Rank papers using citation and publication metadata."""

        return tuple(
            sorted(
                papers,
                key=self._ranking_key,
            )
        )

    @staticmethod
    def _ranking_key(
        paper: Paper,
    ) -> tuple[int, int, date, str]:
        """Return a deterministic ascending sort key."""

        citation_count = paper.citation_count or 0
        publication_year = paper.year or 0
        publication_date = paper.publication_date or date.min

        return (
            -citation_count,
            -publication_year,
            date.max - (publication_date - date.min),
            paper.title.casefold(),
        )
