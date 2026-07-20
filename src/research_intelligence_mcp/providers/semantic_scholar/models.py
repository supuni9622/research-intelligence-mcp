"""Pydantic models for Semantic Scholar API responses.

These models represent external provider contracts only. They must not be
returned directly from MCP tools or exposed outside the provider layer.

Semantic Scholar response objects are mapped into canonical domain models by
the provider mapper.
"""

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SemanticScholarResponseModel(BaseModel):
    """Base model for external Semantic Scholar API responses.

    Semantic Scholar may add response fields over time. Unknown fields are
    therefore ignored to preserve forward compatibility at the provider
    boundary.

    Canonical domain models remain stricter and reject unknown fields.
    """

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class SemanticScholarAuthorResponse(SemanticScholarResponseModel):
    """Author metadata embedded in a Semantic Scholar paper response."""

    author_id: str | None = Field(
        default=None,
        alias="authorId",
        description="Semantic Scholar author identifier.",
    )

    name: str | None = Field(
        default=None,
        description="Author display name.",
    )


class SemanticScholarExternalIdsResponse(SemanticScholarResponseModel):
    """External identifiers associated with a Semantic Scholar paper."""

    doi: str | None = Field(
        default=None,
        alias="DOI",
        description="Digital Object Identifier.",
    )

    arxiv: str | None = Field(
        default=None,
        alias="ArXiv",
        description="arXiv paper identifier.",
    )

    corpus_id: int | str | None = Field(
        default=None,
        alias="CorpusId",
        description="Semantic Scholar corpus identifier.",
    )

    pubmed: str | None = Field(
        default=None,
        alias="PubMed",
        description="PubMed paper identifier.",
    )

    acl: str | None = Field(
        default=None,
        alias="ACL",
        description="ACL Anthology identifier.",
    )

    dblp: str | None = Field(
        default=None,
        alias="DBLP",
        description="DBLP identifier.",
    )

    mag: str | int | None = Field(
        default=None,
        alias="MAG",
        description="Microsoft Academic Graph identifier.",
    )


class SemanticScholarOpenAccessPdfResponse(SemanticScholarResponseModel):
    """Open-access PDF metadata returned by Semantic Scholar."""

    url: str | None = Field(
        default=None,
        description="Direct URL to an open-access PDF.",
    )

    status: str | None = Field(
        default=None,
        description="Provider-supplied open-access status.",
    )

    license: str | None = Field(
        default=None,
        description="Known license for the open-access document.",
    )


class SemanticScholarPublicationVenueResponse(SemanticScholarResponseModel):
    """Structured publication venue returned by Semantic Scholar."""

    venue_id: str | None = Field(
        default=None,
        alias="id",
        description="Semantic Scholar publication venue identifier.",
    )

    name: str | None = Field(
        default=None,
        description="Publication venue name.",
    )

    alternate_names: list[str] = Field(
        default_factory=list,
        alias="alternate_names",
        description="Alternative names for the publication venue.",
    )

    url: str | None = Field(
        default=None,
        description="Publication venue URL.",
    )


class SemanticScholarJournalResponse(SemanticScholarResponseModel):
    """Journal metadata embedded in a paper response."""

    name: str | None = Field(
        default=None,
        description="Journal name.",
    )

    pages: str | None = Field(
        default=None,
        description="Journal page range.",
    )

    volume: str | None = Field(
        default=None,
        description="Journal volume.",
    )


class SemanticScholarPaperResponse(SemanticScholarResponseModel):
    """Paper metadata returned by the Semantic Scholar Academic Graph API."""

    paper_id: str = Field(
        alias="paperId",
        min_length=1,
        description="Semantic Scholar paper identifier.",
    )

    corpus_id: int | None = Field(
        default=None,
        alias="corpusId",
        ge=0,
        description="Semantic Scholar corpus identifier.",
    )

    title: str | None = Field(
        default=None,
        description="Paper title.",
    )

    abstract: str | None = Field(
        default=None,
        description="Paper abstract.",
    )

    year: int | None = Field(
        default=None,
        ge=0,
        description="Publication year.",
    )

    publication_date: date | None = Field(
        default=None,
        alias="publicationDate",
        description="Full publication date when available.",
    )

    venue: str | None = Field(
        default=None,
        description="Publication venue name.",
    )

    publication_venue: SemanticScholarPublicationVenueResponse | None = Field(
        default=None,
        alias="publicationVenue",
        description="Structured publication venue metadata.",
    )

    journal: SemanticScholarJournalResponse | None = Field(
        default=None,
        description="Journal metadata when available.",
    )

    url: str | None = Field(
        default=None,
        description="Semantic Scholar paper page URL.",
    )

    authors: list[SemanticScholarAuthorResponse] = Field(
        default_factory=list,
        description="Paper authors in publication order.",
    )

    external_ids: SemanticScholarExternalIdsResponse | None = Field(
        default=None,
        alias="externalIds",
        description="External paper identifiers.",
    )

    citation_count: int | None = Field(
        default=None,
        alias="citationCount",
        ge=0,
        description="Number of papers citing this paper.",
    )

    influential_citation_count: int | None = Field(
        default=None,
        alias="influentialCitationCount",
        ge=0,
        description="Number of influential citations.",
    )

    reference_count: int | None = Field(
        default=None,
        alias="referenceCount",
        ge=0,
        description="Number of papers referenced by this paper.",
    )

    fields_of_study: list[str] = Field(
        default_factory=list,
        alias="fieldsOfStudy",
        description="Semantic Scholar fields of study.",
    )

    s2_fields_of_study: list[dict[str, Any]] = Field(
        default_factory=list,
        alias="s2FieldsOfStudy",
        description="Structured Semantic Scholar fields of study.",
    )

    publication_types: list[str] = Field(
        default_factory=list,
        alias="publicationTypes",
        description="Provider-supplied publication types.",
    )

    open_access_pdf: SemanticScholarOpenAccessPdfResponse | None = Field(
        default=None,
        alias="openAccessPdf",
        description="Known open-access PDF metadata.",
    )

    is_open_access: bool | None = Field(
        default=None,
        alias="isOpenAccess",
        description="Whether Semantic Scholar marks the paper as open access.",
    )

    @field_validator(
        "title",
        "abstract",
        "venue",
        "url",
        mode="before",
    )
    @classmethod
    def normalize_optional_strings(
        cls,
        value: object,
    ) -> object:
        """Convert empty provider strings to None."""

        if isinstance(value, str) and not value.strip():
            return None

        return value


class SemanticScholarSearchResponse(SemanticScholarResponseModel):
    """Response returned by Semantic Scholar paper search."""

    total: int = Field(
        default=0,
        ge=0,
        description="Total number of matching papers reported by the provider.",
    )

    offset: int = Field(
        default=0,
        ge=0,
        description="Current result offset.",
    )

    next_offset: int | None = Field(
        default=None,
        alias="next",
        ge=0,
        description="Offset for the next result page.",
    )

    data: list[SemanticScholarPaperResponse] = Field(
        default_factory=list,
        description="Papers returned for the search request.",
    )


class SemanticScholarCitationEdgeResponse(SemanticScholarResponseModel):
    """One citation edge returned by the citations endpoint."""

    citing_paper: SemanticScholarPaperResponse | None = Field(
        default=None,
        alias="citingPaper",
        description="Paper that cites the requested paper.",
    )

    contexts: list[str] = Field(
        default_factory=list,
        description="Textual contexts in which the paper was cited.",
    )

    intents: list[str] = Field(
        default_factory=list,
        description="Provider-supplied citation intent labels.",
    )

    is_influential: bool | None = Field(
        default=None,
        alias="isInfluential",
        description="Whether the citation is considered influential.",
    )


class SemanticScholarReferenceEdgeResponse(SemanticScholarResponseModel):
    """One reference edge returned by the references endpoint."""

    cited_paper: SemanticScholarPaperResponse | None = Field(
        default=None,
        alias="citedPaper",
        description="Paper referenced by the requested paper.",
    )

    contexts: list[str] = Field(
        default_factory=list,
        description="Textual contexts associated with the reference.",
    )

    intents: list[str] = Field(
        default_factory=list,
        description="Provider-supplied reference intent labels.",
    )

    is_influential: bool | None = Field(
        default=None,
        alias="isInfluential",
        description="Whether the reference is considered influential.",
    )


class SemanticScholarCitationsResponse(SemanticScholarResponseModel):
    """Paginated response from the paper citations endpoint."""

    offset: int = Field(
        default=0,
        ge=0,
        description="Current citation result offset.",
    )

    next_offset: int | None = Field(
        default=None,
        alias="next",
        ge=0,
        description="Offset for the next citation page.",
    )

    data: list[SemanticScholarCitationEdgeResponse] = Field(
        default_factory=list,
        description="Citation edges returned by the provider.",
    )


class SemanticScholarReferencesResponse(SemanticScholarResponseModel):
    """Paginated response from the paper references endpoint."""

    offset: int = Field(
        default=0,
        ge=0,
        description="Current reference result offset.",
    )

    next_offset: int | None = Field(
        default=None,
        alias="next",
        ge=0,
        description="Offset for the next reference page.",
    )

    data: list[SemanticScholarReferenceEdgeResponse] = Field(
        default_factory=list,
        description="Reference edges returned by the provider.",
    )


class SemanticScholarRecommendationsResponse(SemanticScholarResponseModel):
    """Response returned by the Semantic Scholar Recommendations API."""

    recommended_papers: list[SemanticScholarPaperResponse] = Field(
        default_factory=list,
        alias="recommendedPapers",
        description="Papers recommended for the supplied positive paper.",
    )


class SemanticScholarBatchResponse(SemanticScholarResponseModel):
    """Wrapper used when validating batch paper responses.

    The Semantic Scholar batch endpoint may return an array directly. This
    wrapper provides a convenient internal representation after the raw array
    has been decoded.
    """

    papers: list[SemanticScholarPaperResponse] = Field(
        default_factory=list,
        description="Papers returned by a batch request.",
    )


class SemanticScholarErrorResponse(SemanticScholarResponseModel):
    """Known error body returned by Semantic Scholar APIs."""

    message: str | None = Field(
        default=None,
        description="Provider-supplied error message.",
    )

    code: str | int | None = Field(
        default=None,
        description="Provider-supplied error code.",
    )

    error: str | None = Field(
        default=None,
        description="Alternative provider error description.",
    )

    @property
    def safe_message(self) -> str:
        """Return a normalized error description for internal classification."""

        for value in (
            self.message,
            self.error,
        ):
            if value is not None and value.strip():
                return value.strip()

        return "Semantic Scholar returned an unspecified error."
