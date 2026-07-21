"""Validated MCP schemas for paper metadata and graph tools."""

from __future__ import annotations

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from research_intelligence_mcp.domain.enums import (
    ProviderName,
)
from research_intelligence_mcp.domain.models import (
    Paper,
    PaperAccess,
    PaperReference,
)


class PaperToolSchema(BaseModel):
    """Base schema shared by paper-related MCP tools."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
        validate_default=True,
        use_enum_values=False,
    )


class GetPaperInput(PaperToolSchema):
    """Validated input for retrieving one paper."""

    provider: ProviderName = Field(
        description="Provider used to retrieve the paper.",
    )

    paper_id: str = Field(
        min_length=1,
        max_length=500,
        description="Provider-supported paper identifier.",
        examples=[
            "1706.03762",
            "10.48550/arXiv.1706.03762",
            "204e3073870fae3d05bcbc2f6a8e263d9b72e776",
        ],
    )

    @field_validator("paper_id")
    @classmethod
    def normalize_paper_id(
        cls,
        value: str,
    ) -> str:
        """Normalize whitespace around a paper identifier."""

        normalized = value.strip()

        if not normalized:
            raise ValueError("Paper identifier cannot be empty.")

        return normalized


class PaperGraphInput(GetPaperInput):
    """Validated input shared by citation and reference tools."""

    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of graph relationships to return.",
    )

    offset: int = Field(
        default=0,
        ge=0,
        le=10_000,
        description="Zero-based provider result offset.",
    )


class GetRelatedPapersInput(GetPaperInput):
    """Validated input for related-paper recommendations."""

    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of related papers to return.",
    )

    negative_paper_ids: tuple[str, ...] = Field(
        default_factory=tuple,
        max_length=100,
        description=(
            "Optional paper identifiers that should reduce recommendation similarity."
        ),
    )

    @field_validator(
        "negative_paper_ids",
        mode="before",
    )
    @classmethod
    def normalize_negative_paper_ids(
        cls,
        value: object,
    ) -> object:
        """Normalize and deduplicate negative paper identifiers."""

        if value is None:
            return ()

        if not isinstance(
            value,
            (
                list,
                tuple,
            ),
        ):
            raise ValueError("negative_paper_ids must be a list or tuple.")

        normalized_values: list[str] = []
        seen: set[str] = set()

        for item in value:
            if not isinstance(item, str):
                raise ValueError("Every negative paper identifier must be a string.")

            normalized = item.strip()

            if not normalized:
                raise ValueError("Negative paper identifiers cannot be empty.")

            comparison_key = normalized.casefold()

            if comparison_key in seen:
                continue

            seen.add(comparison_key)
            normalized_values.append(normalized)

        return tuple(normalized_values)


class PaperReferencesResult(PaperToolSchema):
    """Structured result for citation or reference graph retrieval."""

    provider: ProviderName = Field(
        description="Provider used for the graph request.",
    )

    paper_id: str = Field(
        min_length=1,
        max_length=500,
        description="Identifier of the origin paper.",
    )

    offset: int = Field(
        ge=0,
        description="Offset used for the provider request.",
    )

    limit: int = Field(
        ge=1,
        le=100,
        description="Maximum number of relationships requested.",
    )

    returned: int = Field(
        ge=0,
        description="Number of relationships returned.",
    )

    references: tuple[PaperReference, ...] = Field(
        default_factory=tuple,
        description="Canonical citation or reference relationships.",
    )


class RelatedPapersResult(PaperToolSchema):
    """Structured result for related-paper discovery."""

    provider: ProviderName = Field(
        description="Provider used for recommendation retrieval.",
    )

    paper_id: str = Field(
        min_length=1,
        max_length=500,
        description="Identifier of the positive seed paper.",
    )

    limit: int = Field(
        ge=1,
        le=100,
        description="Maximum number of related papers requested.",
    )

    returned: int = Field(
        ge=0,
        description="Number of related papers returned.",
    )

    negative_paper_ids: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Negative recommendation seed identifiers.",
    )

    papers: tuple[Paper, ...] = Field(
        default_factory=tuple,
        description="Canonical related-paper recommendations.",
    )


class PaperAccessResult(PaperToolSchema):
    """Structured result for paper-access resolution."""

    provider: ProviderName = Field(
        description="Provider used to resolve paper access.",
    )

    paper_id: str = Field(
        min_length=1,
        max_length=500,
        description="Identifier supplied by the caller.",
    )

    identifiers: str = Field(
        min_length=1,
        description="Preferred canonical identifier for the resolved paper.",
    )

    title: str = Field(
        min_length=1,
        max_length=1_000,
        description="Resolved paper title.",
    )

    access: PaperAccess = Field(
        description="Canonical access status and available URLs.",
    )
