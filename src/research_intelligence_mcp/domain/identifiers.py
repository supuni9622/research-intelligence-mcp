"""Canonical paper identifier models and normalization rules."""

import re
from typing import Self

from pydantic import Field, field_validator, model_validator

from research_intelligence_mcp.domain.base import DomainModel

_DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)

_ARXIV_PATTERN = re.compile(
    r"^(?:(?:[a-z-]+(?:\.[a-z-]+)?)/\d{7}|"
    r"\d{4}\.\d{4,5})$",
    re.IGNORECASE,
)

_ARXIV_VERSION_PATTERN = re.compile(r"v(?P<version>\d+)$", re.IGNORECASE)

_SEMANTIC_SCHOLAR_PATTERN = re.compile(r"^[A-Za-z0-9]{20,64}$")


def normalize_doi(value: str) -> str:
    """Normalize a DOI into its canonical lowercase identifier."""

    normalized = value.strip()

    prefixes = (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi:",
    )

    lowered = normalized.lower()

    for prefix in prefixes:
        if lowered.startswith(prefix):
            normalized = normalized[len(prefix) :]
            break

    normalized = normalized.strip().lower()

    if not _DOI_PATTERN.fullmatch(normalized):
        raise ValueError("Invalid DOI format.")

    return normalized


def normalize_arxiv_id(value: str) -> str:
    """Normalize an arXiv identifier and remove any version suffix."""

    normalized = value.strip()

    prefixes = (
        "https://arxiv.org/abs/",
        "http://arxiv.org/abs/",
        "https://arxiv.org/pdf/",
        "http://arxiv.org/pdf/",
        "arxiv:",
    )

    lowered = normalized.lower()

    for prefix in prefixes:
        if lowered.startswith(prefix):
            normalized = normalized[len(prefix) :]
            break

    normalized = normalized.removesuffix(".pdf").strip()
    normalized = _ARXIV_VERSION_PATTERN.sub("", normalized)

    if not _ARXIV_PATTERN.fullmatch(normalized):
        raise ValueError("Invalid arXiv identifier format.")

    return normalized.lower()


class PaperIdentifiers(DomainModel):
    """Provider-neutral identifiers associated with a paper."""

    doi: str | None = Field(
        default=None,
        description="Normalized Digital Object Identifier.",
        examples=["10.48550/arxiv.2005.11401"],
    )

    arxiv_id: str | None = Field(
        default=None,
        description="Normalized arXiv identifier without a version suffix.",
        examples=["2005.11401"],
    )

    semantic_scholar_id: str | None = Field(
        default=None,
        min_length=20,
        max_length=64,
        description="Semantic Scholar paper identifier.",
    )

    corpus_id: int | None = Field(
        default=None,
        ge=0,
        description="Semantic Scholar corpus identifier.",
    )

    pmid: str | None = Field(
        default=None,
        pattern=r"^\d+$",
        description="PubMed identifier when available.",
    )

    @field_validator("doi")
    @classmethod
    def validate_doi(cls, value: str | None) -> str | None:
        """Normalize and validate DOI values."""

        if value is None:
            return None

        return normalize_doi(value)

    @field_validator("arxiv_id")
    @classmethod
    def validate_arxiv_id(cls, value: str | None) -> str | None:
        """Normalize and validate arXiv identifiers."""

        if value is None:
            return None

        return normalize_arxiv_id(value)

    @field_validator("semantic_scholar_id")
    @classmethod
    def validate_semantic_scholar_id(
        cls,
        value: str | None,
    ) -> str | None:
        """Validate a Semantic Scholar paper identifier."""

        if value is None:
            return None

        normalized = value.strip()

        if not _SEMANTIC_SCHOLAR_PATTERN.fullmatch(normalized):
            raise ValueError("Invalid Semantic Scholar paper identifier.")

        return normalized

    @model_validator(mode="after")
    def require_at_least_one_identifier(self) -> Self:
        """Require every canonical paper to have a stable identifier."""

        if all(
            identifier is None
            for identifier in (
                self.doi,
                self.arxiv_id,
                self.semantic_scholar_id,
                self.corpus_id,
                self.pmid,
            )
        ):
            raise ValueError("At least one paper identifier is required.")

        return self

    def preferred_identifier(self) -> str:
        """Return the most portable available paper identifier."""

        if self.doi is not None:
            return f"doi:{self.doi}"

        if self.arxiv_id is not None:
            return f"arxiv:{self.arxiv_id}"

        if self.semantic_scholar_id is not None:
            return f"semantic_scholar:{self.semantic_scholar_id}"

        if self.corpus_id is not None:
            return f"corpus_id:{self.corpus_id}"

        if self.pmid is not None:
            return f"pmid:{self.pmid}"

        raise RuntimeError("PaperIdentifiers was created without an identifier.")
