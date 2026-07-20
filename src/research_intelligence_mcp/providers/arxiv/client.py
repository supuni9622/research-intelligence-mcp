"""Asynchronous arXiv API client.

This module owns arXiv-specific HTTP behavior:

- endpoint paths;
- query parameters;
- raw Atom response retrieval;
- bounded retry handling;
- rate-limit response handling;
- provider error normalization.

The client intentionally returns raw Atom XML. XML parsing belongs to the
arXiv parser layer, provider response models belong to the arXiv model layer,
and canonical domain mapping belongs to the arXiv mapper layer.
"""

from __future__ import annotations

import asyncio
import email.utils
import random
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import NoReturn

import httpx

from research_intelligence_mcp.config.settings import Settings
from research_intelligence_mcp.domain.enums import ProviderName
from research_intelligence_mcp.domain.identifiers import normalize_arxiv_id
from research_intelligence_mcp.infrastructure.http import AsyncHttpClient
from research_intelligence_mcp.infrastructure.logging import get_logger
from research_intelligence_mcp.providers.errors import (
    ProviderAuthenticationError,
    ProviderNotFoundError,
    ProviderRateLimitError,
    ProviderRequestError,
    ProviderResponseError,
    ProviderTransportError,
    ProviderUpstreamError,
)

logger = get_logger(__name__)

_PROVIDER = ProviderName.ARXIV
_QUERY_PATH = "/query"

RETRYABLE_STATUS_CODES: frozenset[int] = frozenset(
    {
        408,
        425,
        429,
        500,
        502,
        503,
        504,
    }
)

_XML_CONTENT_TYPES: frozenset[str] = frozenset(
    {
        "application/atom+xml",
        "application/xml",
        "text/xml",
    }
)


class ArxivClient:
    """Raw asynchronous client for the arXiv Atom API."""

    def __init__(
        self,
        *,
        http_client: AsyncHttpClient,
        settings: Settings,
    ) -> None:
        """Initialize the arXiv API client."""

        self._http_client = http_client
        self._settings = settings

    async def search(
        self,
        *,
        search_query: str,
        start: int = 0,
        max_results: int = 10,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> str:
        """Retrieve an Atom feed for an arXiv search query.

        Args:
            search_query: arXiv search expression such as ``all:RAG``.
            start: Zero-based result offset.
            max_results: Maximum number of entries to request.
            sort_by: Optional arXiv sort field.
            sort_order: Optional ascending or descending order.

        Returns:
            Raw Atom XML returned by arXiv.

        Raises:
            ProviderRequestError: If request parameters are invalid.
            ProviderTransportError: If arXiv cannot be reached.
            ProviderRateLimitError: If arXiv rejects the request due to limits.
            ProviderUpstreamError: If arXiv returns a server failure.
            ProviderResponseError: If the response is empty or not XML.
        """

        normalized_query = self._validate_search_query(search_query)

        self._validate_pagination(
            start=start,
            max_results=max_results,
        )

        normalized_sort_by = self._validate_sort_by(sort_by)
        normalized_sort_order = self._validate_sort_order(sort_order)

        params: dict[str, str | int | None] = {
            "search_query": normalized_query,
            "start": start,
            "max_results": max_results,
            "sortBy": normalized_sort_by,
            "sortOrder": normalized_sort_order,
        }

        return await self._request_atom(
            params=params,
        )

    async def get_paper(
        self,
        *,
        arxiv_id: str,
    ) -> str:
        """Retrieve a single paper feed by arXiv identifier.

        Versioned identifiers are accepted. The version suffix is preserved in
        the API request so callers can explicitly retrieve a known version.
        Canonical version removal belongs to the mapper layer.
        """

        normalized_id = self._normalize_request_arxiv_id(arxiv_id)

        return await self._request_atom(
            params={
                "id_list": normalized_id,
                "start": 0,
                "max_results": 1,
            },
        )

    async def get_papers(
        self,
        *,
        arxiv_ids: list[str],
    ) -> str:
        """Retrieve multiple papers by arXiv identifier."""

        if not arxiv_ids:
            raise ProviderRequestError(
                provider=_PROVIDER,
                code="arxiv_empty_id_list",
                message="At least one arXiv identifier is required.",
                retryable=False,
            )

        if len(arxiv_ids) > self._settings.arxiv_max_results_per_request:
            raise ProviderRequestError(
                provider=_PROVIDER,
                code="arxiv_id_list_too_large",
                message=(
                    "The number of arXiv identifiers exceeds the configured "
                    "per-request limit."
                ),
                retryable=False,
                details={
                    "maximum": self._settings.arxiv_max_results_per_request,
                },
            )

        normalized_ids = self._normalize_request_arxiv_ids(arxiv_ids)

        return await self._request_atom(
            params={
                "id_list": ",".join(normalized_ids),
                "start": 0,
                "max_results": len(normalized_ids),
            },
        )

    async def close(self) -> None:
        """Close the managed HTTP client."""

        await self._http_client.close()

    async def _request_atom(
        self,
        *,
        params: Mapping[str, str | int | float | bool | None],
    ) -> str:
        """Execute one Atom request using bounded retries."""

        attempts = self._settings.arxiv_max_retry_attempts

        for attempt_number in range(1, attempts + 1):
            try:
                response = await self._http_client.get(
                    _QUERY_PATH,
                    params=params,
                    headers={
                        "Accept": "application/atom+xml, application/xml;q=0.9",
                    },
                )
            except httpx.TimeoutException as exc:
                if attempt_number >= attempts:
                    raise ProviderTransportError(
                        provider=_PROVIDER,
                        code="arxiv_timeout",
                        message="The arXiv request timed out.",
                        retryable=True,
                    ) from exc

                await self._sleep_before_retry(
                    attempt_number=attempt_number,
                    response=None,
                )
                continue
            except httpx.RequestError as exc:
                if attempt_number >= attempts:
                    raise ProviderTransportError(
                        provider=_PROVIDER,
                        code="arxiv_transport_error",
                        message="arXiv could not be reached.",
                        retryable=True,
                    ) from exc

                await self._sleep_before_retry(
                    attempt_number=attempt_number,
                    response=None,
                )
                continue

            if (
                response.status_code in RETRYABLE_STATUS_CODES
                and attempt_number < attempts
            ):
                await self._sleep_before_retry(
                    attempt_number=attempt_number,
                    response=response,
                )
                continue

            return self._parse_atom_response(response)

        raise ProviderTransportError(
            provider=_PROVIDER,
            code="arxiv_retry_exhausted",
            message="arXiv request retries were exhausted.",
            retryable=True,
        )

    def _parse_atom_response(
        self,
        response: httpx.Response,
    ) -> str:
        """Validate and return a successful raw Atom response."""

        if not response.is_success:
            self._raise_for_error_response(response)

        response_body = response.text.strip()

        if not response_body:
            raise ProviderResponseError(
                provider=_PROVIDER,
                code="arxiv_empty_response",
                message="arXiv returned an empty response.",
                retryable=False,
                status_code=response.status_code,
            )

        content_type = self._normalize_content_type(
            response.headers.get("Content-Type")
        )

        if content_type is not None and content_type not in _XML_CONTENT_TYPES:
            logger.warning(
                "arxiv_unexpected_content_type",
                status_code=response.status_code,
                content_type=content_type,
            )

            raise ProviderResponseError(
                provider=_PROVIDER,
                code="arxiv_unexpected_content_type",
                message="arXiv returned a response that was not Atom XML.",
                retryable=False,
                status_code=response.status_code,
                details={
                    "content_type": content_type,
                },
            )

        if not response_body.startswith("<"):
            raise ProviderResponseError(
                provider=_PROVIDER,
                code="arxiv_invalid_xml_response",
                message="arXiv returned a malformed XML response.",
                retryable=False,
                status_code=response.status_code,
            )

        return response_body

    def _raise_for_error_response(
        self,
        response: httpx.Response,
    ) -> NoReturn:
        """Convert an arXiv HTTP error into a normalized provider error."""

        status_code = response.status_code
        message = self._safe_error_message(response)

        if status_code in {401, 403}:
            raise ProviderAuthenticationError(
                provider=_PROVIDER,
                code="arxiv_access_denied",
                message=message,
                retryable=False,
                status_code=status_code,
            )

        if status_code == 404:
            raise ProviderNotFoundError(
                provider=_PROVIDER,
                code="arxiv_not_found",
                message=message,
                retryable=False,
                status_code=status_code,
            )

        if status_code == 429:
            raise ProviderRateLimitError(
                provider=_PROVIDER,
                code="arxiv_rate_limited",
                message=message,
                retryable=True,
                status_code=status_code,
                retry_after_seconds=self._retry_after_seconds(response),
            )

        if 400 <= status_code < 500:
            raise ProviderRequestError(
                provider=_PROVIDER,
                code="arxiv_request_rejected",
                message=message,
                retryable=False,
                status_code=status_code,
            )

        if status_code >= 500:
            raise ProviderUpstreamError(
                provider=_PROVIDER,
                code="arxiv_upstream_failure",
                message=message,
                retryable=True,
                status_code=status_code,
            )

        raise ProviderResponseError(
            provider=_PROVIDER,
            code="arxiv_unexpected_status",
            message=message,
            retryable=False,
            status_code=status_code,
        )

    async def _sleep_before_retry(
        self,
        *,
        attempt_number: int,
        response: httpx.Response | None,
    ) -> None:
        """Sleep using Retry-After or exponential backoff with jitter."""

        retry_after = (
            self._retry_after_seconds(response) if response is not None else None
        )

        if retry_after is None:
            minimum = self._settings.arxiv_retry_min_seconds
            maximum = self._settings.arxiv_retry_max_seconds

            exponential_delay = minimum * (2 ** (attempt_number - 1))
            bounded_delay = min(exponential_delay, maximum)
            jitter_limit = min(1.0, bounded_delay * 0.25)

            retry_after = bounded_delay + random.uniform(
                0.0,
                jitter_limit,
            )

        retry_after = min(
            retry_after,
            self._settings.arxiv_retry_max_seconds,
        )

        logger.warning(
            "arxiv_request_retrying",
            attempt_number=attempt_number,
            sleep_seconds=retry_after,
            status_code=(response.status_code if response is not None else None),
        )

        await asyncio.sleep(retry_after)

    @staticmethod
    def _retry_after_seconds(
        response: httpx.Response | None,
    ) -> float | None:
        """Parse Retry-After seconds or HTTP-date values."""

        if response is None:
            return None

        value = response.headers.get("Retry-After")

        if value is None:
            return None

        stripped_value = value.strip()

        try:
            return max(float(stripped_value), 0.0)
        except ValueError:
            pass

        try:
            retry_datetime = email.utils.parsedate_to_datetime(stripped_value)
        except (TypeError, ValueError, OverflowError):
            return None

        if retry_datetime.tzinfo is None:
            retry_datetime = retry_datetime.replace(tzinfo=UTC)

        seconds = (retry_datetime - datetime.now(UTC)).total_seconds()

        return max(seconds, 0.0)

    def _validate_pagination(
        self,
        *,
        start: int,
        max_results: int,
    ) -> None:
        """Validate arXiv pagination parameters."""

        if start < 0:
            raise ProviderRequestError(
                provider=_PROVIDER,
                code="arxiv_invalid_start",
                message="arXiv result offset cannot be negative.",
                retryable=False,
            )

        if max_results < 1:
            raise ProviderRequestError(
                provider=_PROVIDER,
                code="arxiv_invalid_max_results",
                message="arXiv max_results must be at least one.",
                retryable=False,
            )

        if max_results > self._settings.arxiv_max_results_per_request:
            raise ProviderRequestError(
                provider=_PROVIDER,
                code="arxiv_max_results_exceeded",
                message=(
                    "Requested arXiv result count exceeds the configured "
                    "per-request limit."
                ),
                retryable=False,
                details={
                    "maximum": self._settings.arxiv_max_results_per_request,
                },
            )

    @staticmethod
    def _validate_search_query(search_query: str) -> str:
        """Validate and normalize an arXiv search expression."""

        normalized = " ".join(search_query.split())

        if not normalized:
            raise ProviderRequestError(
                provider=_PROVIDER,
                code="arxiv_empty_search_query",
                message="arXiv search query cannot be empty.",
                retryable=False,
            )

        if len(normalized) > 2_000:
            raise ProviderRequestError(
                provider=_PROVIDER,
                code="arxiv_search_query_too_long",
                message="arXiv search query is too long.",
                retryable=False,
            )

        return normalized

    @staticmethod
    def _validate_sort_by(value: str | None) -> str | None:
        """Validate an optional arXiv sort field."""

        if value is None:
            return None

        allowed_values = {
            "relevance",
            "lastUpdatedDate",
            "submittedDate",
        }

        if value not in allowed_values:
            raise ProviderRequestError(
                provider=_PROVIDER,
                code="arxiv_invalid_sort_by",
                message=(
                    "arXiv sort_by must be relevance, "
                    "lastUpdatedDate, or submittedDate."
                ),
                retryable=False,
            )

        return value

    @staticmethod
    def _validate_sort_order(value: str | None) -> str | None:
        """Validate an optional arXiv sort direction."""

        if value is None:
            return None

        allowed_values = {
            "ascending",
            "descending",
        }

        if value not in allowed_values:
            raise ProviderRequestError(
                provider=_PROVIDER,
                code="arxiv_invalid_sort_order",
                message=("arXiv sort_order must be ascending or descending."),
                retryable=False,
            )

        return value

    @staticmethod
    def _normalize_request_arxiv_id(value: str) -> str:
        """Normalize an identifier while preserving its version suffix."""

        stripped = value.strip()

        if not stripped:
            raise ProviderRequestError(
                provider=_PROVIDER,
                code="arxiv_invalid_paper_id",
                message="arXiv identifier cannot be empty.",
                retryable=False,
            )

        prefixes = (
            "https://arxiv.org/abs/",
            "http://arxiv.org/abs/",
            "https://arxiv.org/pdf/",
            "http://arxiv.org/pdf/",
            "arxiv:",
        )

        lowered = stripped.lower()

        for prefix in prefixes:
            if lowered.startswith(prefix):
                stripped = stripped[len(prefix) :]
                break

        normalized = stripped.removesuffix(".pdf").strip()

        base_identifier = normalized
        version_position = normalized.lower().rfind("v")

        if version_position > 0:
            possible_version = normalized[version_position + 1 :]

            if possible_version.isdigit():
                base_identifier = normalized[:version_position]

        try:
            normalize_arxiv_id(base_identifier)
        except ValueError as exc:
            raise ProviderRequestError(
                provider=_PROVIDER,
                code="arxiv_invalid_paper_id",
                message="Invalid arXiv identifier.",
                retryable=False,
            ) from exc

        return normalized

    @classmethod
    def _normalize_request_arxiv_ids(
        cls,
        values: list[str],
    ) -> list[str]:
        """Normalize and deduplicate arXiv identifiers."""

        normalized_values: list[str] = []
        seen: set[str] = set()

        for value in values:
            normalized = cls._normalize_request_arxiv_id(value)
            comparison_key = normalized.casefold()

            if comparison_key in seen:
                continue

            seen.add(comparison_key)
            normalized_values.append(normalized)

        return normalized_values

    @staticmethod
    def _safe_error_message(response: httpx.Response) -> str:
        """Return a bounded safe message for an arXiv error response."""

        fallback = "arXiv returned an HTTP error."
        content_type = ArxivClient._normalize_content_type(
            response.headers.get("Content-Type")
        )

        if content_type not in _XML_CONTENT_TYPES:
            return fallback

        body = " ".join(response.text.split())

        if not body:
            return fallback

        return body[:500]

    @staticmethod
    def _normalize_content_type(value: str | None) -> str | None:
        """Normalize an HTTP Content-Type header."""

        if value is None:
            return None

        normalized = value.split(";", maxsplit=1)[0].strip().lower()

        return normalized or None
