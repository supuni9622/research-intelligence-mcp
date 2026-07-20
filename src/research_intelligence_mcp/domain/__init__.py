"""Canonical domain contracts for Research Intelligence MCP."""

from research_intelligence_mcp.domain.enums import (
    AccessStatus,
    IdentifierType,
    PaperRelationType,
    ProviderName,
    SearchSort,
)
from research_intelligence_mcp.domain.identifiers import (
    PaperIdentifiers,
    normalize_arxiv_id,
    normalize_doi,
)
from research_intelligence_mcp.domain.models import (
    Author,
    Paper,
    PaperAccess,
    PaperReference,
)
from research_intelligence_mcp.domain.requests import (
    PaginationMetadata,
    ProviderFailure,
    SearchRequest,
    SearchResult,
)

__all__ = [
    "AccessStatus",
    "Author",
    "IdentifierType",
    "PaginationMetadata",
    "Paper",
    "PaperAccess",
    "PaperIdentifiers",
    "PaperReference",
    "PaperRelationType",
    "ProviderFailure",
    "ProviderName",
    "SearchRequest",
    "SearchResult",
    "SearchSort",
    "normalize_arxiv_id",
    "normalize_doi",
]
