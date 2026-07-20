"""Deduplication of canonical academic papers."""

from __future__ import annotations

import re

from research_intelligence_mcp.domain.models import Paper


class PaperDeduplicator:
    """Remove duplicate papers using canonical identifiers."""

    def deduplicate(
        self,
        papers: tuple[Paper, ...],
    ) -> tuple[Paper, ...]:
        """Deduplicate papers and preserve source provenance."""

        deduplicated: dict[str, Paper] = {}

        for paper in papers:
            key = self._deduplication_key(paper)

            existing = deduplicated.get(key)

            if existing is None:
                deduplicated[key] = paper
                continue

            deduplicated[key] = self._merge(
                existing=existing,
                incoming=paper,
            )

        return tuple(deduplicated.values())

    def _deduplication_key(
        self,
        paper: Paper,
    ) -> str:
        """Build the strongest available deduplication key."""

        identifiers = paper.identifiers

        if identifiers.doi is not None:
            return f"doi:{identifiers.doi.casefold()}"

        if identifiers.arxiv_id is not None:
            return f"arxiv:{identifiers.arxiv_id.casefold()}"

        if identifiers.semantic_scholar_id is not None:
            return f"semantic_scholar:{identifiers.semantic_scholar_id.casefold()}"

        normalized_title = self._normalize_title(paper.title)
        year = paper.year if paper.year is not None else "unknown"

        return f"title:{normalized_title}:year:{year}"

    @staticmethod
    def _normalize_title(
        title: str,
    ) -> str:
        """Normalize a title for fallback comparison."""

        normalized = re.sub(
            r"[^\w\s]",
            " ",
            title.casefold(),
        )

        return " ".join(normalized.split())

    @staticmethod
    def _merge(
        *,
        existing: Paper,
        incoming: Paper,
    ) -> Paper:
        """Merge duplicate records without losing provenance."""

        merged_sources = tuple(dict.fromkeys(existing.sources + incoming.sources))

        abstract = existing.abstract or incoming.abstract

        if (
            existing.abstract is not None
            and incoming.abstract is not None
            and len(incoming.abstract) > len(existing.abstract)
        ):
            abstract = incoming.abstract

        citation_count = PaperDeduplicator._maximum_optional_integer(
            existing.citation_count,
            incoming.citation_count,
        )

        reference_count = PaperDeduplicator._maximum_optional_integer(
            existing.reference_count,
            incoming.reference_count,
        )

        return existing.model_copy(
            update={
                "abstract": abstract,
                "citation_count": citation_count,
                "reference_count": reference_count,
                "sources": merged_sources,
            }
        )

    @staticmethod
    def _maximum_optional_integer(
        first: int | None,
        second: int | None,
    ) -> int | None:
        """Return the maximum known integer."""

        values = tuple(value for value in (first, second) if value is not None)

        return max(values) if values else None
