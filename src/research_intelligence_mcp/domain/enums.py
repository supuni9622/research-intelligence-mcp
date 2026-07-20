"""Enumerations used by canonical research domain models."""

from enum import StrEnum


class ProviderName(StrEnum):
    """Supported academic research providers."""

    SEMANTIC_SCHOLAR = "semantic_scholar"
    ARXIV = "arxiv"


class IdentifierType(StrEnum):
    """Canonical paper identifier types."""

    DOI = "doi"
    ARXIV = "arxiv"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    CORPUS_ID = "corpus_id"
    PMID = "pmid"


class AccessStatus(StrEnum):
    """Availability state of a research paper."""

    OPEN_ACCESS = "open_access"
    CLOSED_ACCESS = "closed_access"
    UNKNOWN = "unknown"


class PaperRelationType(StrEnum):
    """Relationship between a paper and another paper."""

    CITATION = "citation"
    REFERENCE = "reference"
    RELATED = "related"


class SearchSort(StrEnum):
    """Supported paper search ordering strategies."""

    RELEVANCE = "relevance"
    PUBLICATION_DATE = "publication_date"
    CITATION_COUNT = "citation_count"
