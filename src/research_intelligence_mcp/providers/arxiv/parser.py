"""Secure parser for arXiv Atom API responses.

This module converts raw arXiv Atom XML into typed provider response models.

It deliberately uses defusedxml rather than Python's unrestricted XML parser
to reject dangerous entity expansion and related XML attacks.

No HTTP behavior or canonical domain mapping belongs in this module.
"""

from __future__ import annotations

from datetime import datetime
from typing import Final
from xml.etree.ElementTree import Element, ParseError

from defusedxml import ElementTree as DefusedElementTree
from defusedxml.common import DefusedXmlException
from pydantic import ValidationError

from research_intelligence_mcp.domain.enums import ProviderName
from research_intelligence_mcp.infrastructure.logging import get_logger
from research_intelligence_mcp.providers.arxiv.models import (
    ArxivAuthorResponse,
    ArxivCategoryResponse,
    ArxivEntryResponse,
    ArxivFeedResponse,
    ArxivLinkResponse,
)
from research_intelligence_mcp.providers.errors import (
    ProviderResponseError,
)

logger = get_logger(__name__)

_PROVIDER: Final = ProviderName.ARXIV

ATOM_NAMESPACE: Final = "http://www.w3.org/2005/Atom"
ARXIV_NAMESPACE: Final = "http://arxiv.org/schemas/atom"
OPENSEARCH_NAMESPACE: Final = "http://a9.com/-/spec/opensearch/1.1/"

NAMESPACES: Final[dict[str, str]] = {
    "atom": ATOM_NAMESPACE,
    "arxiv": ARXIV_NAMESPACE,
    "opensearch": OPENSEARCH_NAMESPACE,
}


class ArxivParser:
    """Parse raw arXiv Atom XML into provider response models."""

    @classmethod
    def parse_feed(
        cls,
        xml: str,
    ) -> ArxivFeedResponse:
        """Parse an arXiv Atom feed.

        Args:
            xml: Raw Atom XML returned by the arXiv API.

        Returns:
            A validated arXiv feed response.

        Raises:
            ProviderResponseError: If XML is empty, unsafe, malformed, or
                inconsistent with the expected arXiv response structure.
        """

        normalized_xml = xml.strip()

        if not normalized_xml:
            raise ProviderResponseError(
                provider=_PROVIDER,
                code="arxiv_empty_xml",
                message="arXiv returned an empty XML document.",
                retryable=False,
            )

        root = cls._parse_xml_root(normalized_xml)

        if root.tag != cls._qualified_name(
            ATOM_NAMESPACE,
            "feed",
        ):
            raise ProviderResponseError(
                provider=_PROVIDER,
                code="arxiv_unexpected_xml_root",
                message="arXiv returned XML with an unexpected root element.",
                retryable=False,
                details={
                    "root_tag": root.tag,
                },
            )

        entries = [
            cls._parse_entry(entry_element)
            for entry_element in root.findall(
                "atom:entry",
                NAMESPACES,
            )
        ]

        payload = {
            "id": cls._optional_text(
                root.find(
                    "atom:id",
                    NAMESPACES,
                )
            ),
            "title": cls._optional_text(
                root.find(
                    "atom:title",
                    NAMESPACES,
                )
            ),
            "updated": cls._parse_optional_datetime(
                cls._optional_text(
                    root.find(
                        "atom:updated",
                        NAMESPACES,
                    )
                ),
                field_name="feed.updated",
            ),
            "total_results": cls._parse_non_negative_integer(
                cls._optional_text(
                    root.find(
                        "opensearch:totalResults",
                        NAMESPACES,
                    )
                ),
                field_name="totalResults",
                default=0,
            ),
            "start_index": cls._parse_non_negative_integer(
                cls._optional_text(
                    root.find(
                        "opensearch:startIndex",
                        NAMESPACES,
                    )
                ),
                field_name="startIndex",
                default=0,
            ),
            "items_per_page": cls._parse_non_negative_integer(
                cls._optional_text(
                    root.find(
                        "opensearch:itemsPerPage",
                        NAMESPACES,
                    )
                ),
                field_name="itemsPerPage",
                default=len(entries),
            ),
            "entries": entries,
        }

        try:
            return ArxivFeedResponse.model_validate(payload)
        except ValidationError as exc:
            logger.warning(
                "arxiv_feed_validation_failed",
                validation_errors=exc.errors(
                    include_url=False,
                ),
            )

            raise ProviderResponseError(
                provider=_PROVIDER,
                code="arxiv_invalid_feed",
                message=("arXiv returned an unexpected Atom feed structure."),
                retryable=False,
                details={
                    "validation_errors": exc.errors(
                        include_url=False,
                    ),
                },
            ) from exc

    @classmethod
    def _parse_entry(
        cls,
        element: Element,
    ) -> ArxivEntryResponse:
        """Parse one Atom entry."""

        payload = {
            "id": cls._optional_text(
                element.find(
                    "atom:id",
                    NAMESPACES,
                )
            ),
            "title": cls._optional_text(
                element.find(
                    "atom:title",
                    NAMESPACES,
                )
            ),
            "summary": cls._optional_text(
                element.find(
                    "atom:summary",
                    NAMESPACES,
                )
            ),
            "published": cls._parse_optional_datetime(
                cls._optional_text(
                    element.find(
                        "atom:published",
                        NAMESPACES,
                    )
                ),
                field_name="entry.published",
            ),
            "updated": cls._parse_optional_datetime(
                cls._optional_text(
                    element.find(
                        "atom:updated",
                        NAMESPACES,
                    )
                ),
                field_name="entry.updated",
            ),
            "authors": [
                cls._parse_author(author_element)
                for author_element in element.findall(
                    "atom:author",
                    NAMESPACES,
                )
            ],
            "links": cls._parse_links(element),
            "categories": cls._parse_categories(element),
            "primary_category": cls._parse_primary_category(element),
            "comment": cls._optional_text(
                element.find(
                    "arxiv:comment",
                    NAMESPACES,
                )
            ),
            "journal_reference": cls._optional_text(
                element.find(
                    "arxiv:journal_ref",
                    NAMESPACES,
                )
            ),
            "doi": cls._optional_text(
                element.find(
                    "arxiv:doi",
                    NAMESPACES,
                )
            ),
        }

        try:
            return ArxivEntryResponse.model_validate(payload)
        except ValidationError as exc:
            logger.warning(
                "arxiv_entry_validation_failed",
                entry_id=payload.get("id"),
                validation_errors=exc.errors(
                    include_url=False,
                ),
            )

            raise ProviderResponseError(
                provider=_PROVIDER,
                code="arxiv_invalid_entry",
                message=("arXiv returned an invalid paper entry."),
                retryable=False,
                details={
                    "entry_id": payload.get("id"),
                    "validation_errors": exc.errors(
                        include_url=False,
                    ),
                },
            ) from exc

    @classmethod
    def _parse_author(
        cls,
        element: Element,
    ) -> ArxivAuthorResponse:
        """Parse one Atom author."""

        payload = {
            "name": cls._optional_text(
                element.find(
                    "atom:name",
                    NAMESPACES,
                )
            ),
            "affiliations": [
                affiliation
                for affiliation_element in element.findall(
                    "arxiv:affiliation",
                    NAMESPACES,
                )
                if (affiliation := cls._optional_text(affiliation_element)) is not None
            ],
        }

        try:
            return ArxivAuthorResponse.model_validate(payload)
        except ValidationError as exc:
            raise ProviderResponseError(
                provider=_PROVIDER,
                code="arxiv_invalid_author",
                message=("arXiv returned an invalid author entry."),
                retryable=False,
                details={
                    "validation_errors": exc.errors(
                        include_url=False,
                    ),
                },
            ) from exc

    @classmethod
    def _parse_links(
        cls,
        element: Element,
    ) -> list[ArxivLinkResponse]:
        """Parse valid Atom link elements."""

        links: list[ArxivLinkResponse] = []

        for link_element in element.findall(
            "atom:link",
            NAMESPACES,
        ):
            href = cls._clean_optional_string(link_element.attrib.get("href"))

            if href is None:
                continue

            try:
                link = ArxivLinkResponse.model_validate(
                    {
                        "href": href,
                        "rel": cls._clean_optional_string(
                            link_element.attrib.get("rel")
                        ),
                        "type": cls._clean_optional_string(
                            link_element.attrib.get("type")
                        ),
                        "title": cls._clean_optional_string(
                            link_element.attrib.get("title")
                        ),
                    }
                )
            except ValidationError as exc:
                raise ProviderResponseError(
                    provider=_PROVIDER,
                    code="arxiv_invalid_link",
                    message=("arXiv returned invalid link metadata."),
                    retryable=False,
                    details={
                        "validation_errors": exc.errors(
                            include_url=False,
                        ),
                    },
                ) from exc

            links.append(link)

        return links

    @classmethod
    def _parse_categories(
        cls,
        element: Element,
    ) -> list[ArxivCategoryResponse]:
        """Parse and deduplicate Atom category elements."""

        categories: list[ArxivCategoryResponse] = []
        seen: set[str] = set()

        for category_element in element.findall(
            "atom:category",
            NAMESPACES,
        ):
            category = cls._parse_category_element(category_element)

            if category is None:
                continue

            key = category.term.casefold()

            if key in seen:
                continue

            seen.add(key)
            categories.append(category)

        return categories

    @classmethod
    def _parse_primary_category(
        cls,
        element: Element,
    ) -> ArxivCategoryResponse | None:
        """Parse the arXiv primary category extension."""

        primary_element = element.find(
            "arxiv:primary_category",
            NAMESPACES,
        )

        if primary_element is None:
            return None

        return cls._parse_category_element(primary_element)

    @classmethod
    def _parse_category_element(
        cls,
        element: Element,
    ) -> ArxivCategoryResponse | None:
        """Parse one category-like XML element."""

        term = cls._clean_optional_string(element.attrib.get("term"))

        if term is None:
            return None

        try:
            return ArxivCategoryResponse.model_validate(
                {
                    "term": term,
                    "scheme": cls._clean_optional_string(element.attrib.get("scheme")),
                    "label": cls._clean_optional_string(element.attrib.get("label")),
                }
            )
        except ValidationError as exc:
            raise ProviderResponseError(
                provider=_PROVIDER,
                code="arxiv_invalid_category",
                message=("arXiv returned invalid category metadata."),
                retryable=False,
                details={
                    "validation_errors": exc.errors(
                        include_url=False,
                    ),
                },
            ) from exc

    @staticmethod
    def _parse_xml_root(
        xml: str,
    ) -> Element:
        """Securely parse an XML document root."""

        try:
            return DefusedElementTree.fromstring(xml)
        except DefusedXmlException as exc:
            raise ProviderResponseError(
                provider=_PROVIDER,
                code="arxiv_unsafe_xml",
                message=("arXiv returned XML containing prohibited constructs."),
                retryable=False,
            ) from exc
        except ParseError as exc:
            raise ProviderResponseError(
                provider=_PROVIDER,
                code="arxiv_malformed_xml",
                message="arXiv returned malformed XML.",
                retryable=False,
            ) from exc

    @staticmethod
    def _parse_optional_datetime(
        value: str | None,
        *,
        field_name: str,
    ) -> datetime | None:
        """Parse an optional ISO-8601 datetime."""

        if value is None:
            return None

        normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value

        try:
            return datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ProviderResponseError(
                provider=_PROVIDER,
                code="arxiv_invalid_datetime",
                message=("arXiv returned an invalid timestamp."),
                retryable=False,
                details={
                    "field": field_name,
                    "value": value,
                },
            ) from exc

    @staticmethod
    def _parse_non_negative_integer(
        value: str | None,
        *,
        field_name: str,
        default: int,
    ) -> int:
        """Parse a non-negative OpenSearch integer."""

        if value is None:
            return default

        try:
            parsed_value = int(value)
        except ValueError as exc:
            raise ProviderResponseError(
                provider=_PROVIDER,
                code="arxiv_invalid_pagination",
                message=("arXiv returned invalid pagination metadata."),
                retryable=False,
                details={
                    "field": field_name,
                    "value": value,
                },
            ) from exc

        if parsed_value < 0:
            raise ProviderResponseError(
                provider=_PROVIDER,
                code="arxiv_invalid_pagination",
                message=("arXiv returned negative pagination metadata."),
                retryable=False,
                details={
                    "field": field_name,
                    "value": parsed_value,
                },
            )

        return parsed_value

    @staticmethod
    def _optional_text(
        element: Element | None,
    ) -> str | None:
        """Read and normalize an element's text content."""

        if element is None:
            return None

        text = "".join(element.itertext())

        return ArxivParser._clean_optional_string(text)

    @staticmethod
    def _clean_optional_string(
        value: str | None,
    ) -> str | None:
        """Normalize whitespace and convert blanks to None."""

        if value is None:
            return None

        normalized = " ".join(value.split())

        return normalized or None

    @staticmethod
    def _qualified_name(
        namespace: str,
        local_name: str,
    ) -> str:
        """Build an ElementTree qualified XML name."""

        return f"{{{namespace}}}{local_name}"
