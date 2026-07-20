"""Canonical paper-provider interface."""

from __future__ import annotations

from typing import Protocol

from research_intelligence_mcp.domain.enums import (
    ProviderName,
)
from research_intelligence_mcp.domain.models import (
    Paper,
    PaperReference,
)
from research_intelligence_mcp.domain.requests import (
    SearchRequest,
    SearchResult,
)


class PaperProvider(Protocol):
    """Provider-independent academic-paper capability contract."""

    @property
    def name(self) -> ProviderName:
        """Return the canonical provider identifier."""

    async def search_papers(
        self,
        request: SearchRequest,
    ) -> SearchResult:
        """Search papers."""

    async def get_paper(
        self,
        paper_id: str,
    ) -> Paper:
        """Retrieve one paper."""

    async def get_citations(
        self,
        paper_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PaperReference]:
        """Retrieve papers citing the requested paper."""

    async def get_references(
        self,
        paper_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PaperReference]:
        """Retrieve papers referenced by the requested paper."""

    async def get_related_papers(
        self,
        paper_id: str,
        *,
        limit: int = 10,
        negative_paper_ids: list[str] | None = None,
    ) -> list[Paper]:
        """Retrieve related papers."""

    async def close(self) -> None:
        """Release provider resources."""
