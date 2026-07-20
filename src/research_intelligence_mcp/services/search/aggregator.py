"""Aggregation of canonical provider search results."""

from __future__ import annotations

from dataclasses import dataclass

from research_intelligence_mcp.domain.enums import ProviderName
from research_intelligence_mcp.domain.models import Paper
from research_intelligence_mcp.domain.requests import ProviderFailure, SearchResult


@dataclass(
    frozen=True,
    slots=True,
)
class AggregatedSearchResults:
    """Internal aggregation result before ranking and pagination."""

    papers: tuple[Paper, ...]
    providers_requested: tuple[ProviderName, ...]
    providers_succeeded: tuple[ProviderName, ...]
    failures: tuple[ProviderFailure, ...]
    warnings: tuple[str, ...]
    total: int | None
    has_more: bool


class SearchResultAggregator:
    """Combine provider responses into an internal result."""

    def aggregate(
        self,
        results: tuple[SearchResult, ...],
    ) -> AggregatedSearchResults:
        """Aggregate provider results without applying final pagination."""

        papers: list[Paper] = []
        requested: list[ProviderName] = []
        succeeded: list[ProviderName] = []
        failures: list[ProviderFailure] = []
        warnings: list[str] = []
        known_totals: list[int] = []
        has_more = False

        for result in results:
            papers.extend(result.papers)
            requested.extend(result.providers_requested)
            succeeded.extend(result.providers_succeeded)
            failures.extend(result.failures)
            warnings.extend(result.warnings)

            if result.pagination.total is not None:
                known_totals.append(result.pagination.total)

            has_more = has_more or result.pagination.has_more

        return AggregatedSearchResults(
            papers=tuple(papers),
            providers_requested=tuple(dict.fromkeys(requested)),
            providers_succeeded=tuple(dict.fromkeys(succeeded)),
            failures=tuple(failures),
            warnings=tuple(dict.fromkeys(warnings)),
            total=sum(known_totals) if known_totals else None,
            has_more=has_more,
        )
