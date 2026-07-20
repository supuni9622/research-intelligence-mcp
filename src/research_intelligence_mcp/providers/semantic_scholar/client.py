"""Async Semantic Scholar API client.

This module owns Semantic Scholar-specific HTTP behavior:

- endpoint paths;
- query parameters;
- requested fields;
- optional API-key authentication;
- response validation;
- bounded retry handling;
- rate-limit handling;
- provider error normalization.

The client returns provider response models and never returns canonical
domain models.
"""

from __future__ import annotations

import asyncio
import email.utils
import random
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, NoReturn, TypeVar

import httpx
from pydantic import ValidationError

from research_intelligence_mcp.config.settings import Settings
from research_intelligence_mcp.domain.enums import ProviderName
from research_intelligence_mcp.infrastructure.http import (
    AsyncHttpClient,
)
from research_intelligence_mcp.infrastructure.logging import (
    get_logger,
)
from research_intelligence_mcp.providers.errors import (
    ProviderAuthenticationError,
    ProviderNotFoundError,
    ProviderRateLimitError,
    ProviderRequestError,
    ProviderResponseError,
    ProviderTransportError,
    ProviderUpstreamError,
)
from research_intelligence_mcp.providers.semantic_scholar.models import (
    SemanticScholarCitationsResponse,
    SemanticScholarErrorResponse,
    SemanticScholarPaperResponse,
    SemanticScholarRecommendationsResponse,
    SemanticScholarReferencesResponse,
    SemanticScholarResponseModel,
    SemanticScholarSearchResponse,
)

logger = get_logger(__name__)

ResponseModelT = TypeVar(
    "ResponseModelT",
    bound=SemanticScholarResponseModel,
)

_PROVIDER = ProviderName.SEMANTIC_SCHOLAR

PAPER_FIELDS: tuple[str, ...] = (
    "paperId",
    "corpusId",
    "url",
    "title",
    "abstract",
    "venue",
    "publicationVenue",
    "year",
    "publicationDate",
    "externalIds",
    "authors",
    "citationCount",
    "influentialCitationCount",
    "referenceCount",
    "fieldsOfStudy",
    "s2FieldsOfStudy",
    "publicationTypes",
    "journal",
    "isOpenAccess",
    "openAccessPdf",
)

CITATION_FIELDS: tuple[str, ...] = (
    "contexts",
    "intents",
    "isInfluential",
    *tuple(f"citingPaper.{field}" for field in PAPER_FIELDS),
)

REFERENCE_FIELDS: tuple[str, ...] = (
    "contexts",
    "intents",
    "isInfluential",
    *tuple(f"citedPaper.{field}" for field in PAPER_FIELDS),
)

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


class SemanticScholarClient:
    """Typed asynchronous client for Semantic Scholar APIs."""

    def __init__(
        self,
        *,
        graph_http_client: AsyncHttpClient,
        recommendations_http_client: AsyncHttpClient,
        settings: Settings,
    ) -> None:
        """Initialize the Semantic Scholar client."""

        self._graph_http_client = graph_http_client
        self._recommendations_http_client = recommendations_http_client
        self._settings = settings

    async def search_papers(
        self,
        *,
        query: str,
        limit: int,
        offset: int = 0,
        year_from: int | None = None,
        year_to: int | None = None,
        open_access_only: bool = False,
    ) -> SemanticScholarSearchResponse:
        """Search Semantic Scholar papers."""

        params: dict[
            str,
            str | int | bool | None,
        ] = {
            "query": query,
            "limit": limit,
            "offset": offset,
            "fields": ",".join(PAPER_FIELDS),
        }

        year_filter = self._build_year_filter(
            year_from=year_from,
            year_to=year_to,
        )

        if year_filter is not None:
            params["year"] = year_filter

        if open_access_only:
            params["openAccessPdf"] = True

        return await self._request_model(
            client=self._graph_http_client,
            method="GET",
            path="/paper/search",
            response_model=(SemanticScholarSearchResponse),
            params=params,
        )

    async def get_paper(
        self,
        *,
        paper_id: str,
    ) -> SemanticScholarPaperResponse:
        """Retrieve one paper by a supported identifier."""

        normalized_paper_id = self._validate_paper_id(paper_id)

        return await self._request_model(
            client=self._graph_http_client,
            method="GET",
            path=f"/paper/{normalized_paper_id}",
            response_model=(SemanticScholarPaperResponse),
            params={
                "fields": ",".join(PAPER_FIELDS),
            },
        )

    async def get_citations(
        self,
        *,
        paper_id: str,
        limit: int,
        offset: int = 0,
    ) -> SemanticScholarCitationsResponse:
        """Retrieve papers citing the requested paper."""

        normalized_paper_id = self._validate_paper_id(paper_id)

        return await self._request_model(
            client=self._graph_http_client,
            method="GET",
            path=(f"/paper/{normalized_paper_id}/citations"),
            response_model=(SemanticScholarCitationsResponse),
            params={
                "limit": limit,
                "offset": offset,
                "fields": ",".join(CITATION_FIELDS),
            },
        )

    async def get_references(
        self,
        *,
        paper_id: str,
        limit: int,
        offset: int = 0,
    ) -> SemanticScholarReferencesResponse:
        """Retrieve papers referenced by the requested paper."""

        normalized_paper_id = self._validate_paper_id(paper_id)

        return await self._request_model(
            client=self._graph_http_client,
            method="GET",
            path=(f"/paper/{normalized_paper_id}/references"),
            response_model=(SemanticScholarReferencesResponse),
            params={
                "limit": limit,
                "offset": offset,
                "fields": ",".join(REFERENCE_FIELDS),
            },
        )

    async def get_recommendations(
        self,
        *,
        positive_paper_ids: list[str],
        negative_paper_ids: list[str] | None = None,
        limit: int = 10,
    ) -> SemanticScholarRecommendationsResponse:
        """Retrieve papers related to positive examples."""

        normalized_positive_ids = self._normalize_paper_ids(positive_paper_ids)

        if not normalized_positive_ids:
            raise ProviderRequestError(
                provider=_PROVIDER,
                code="invalid_positive_paper_ids",
                message=("At least one positive paper identifier is required."),
                retryable=False,
            )

        normalized_negative_ids = self._normalize_paper_ids(negative_paper_ids or [])

        return await self._request_model(
            client=(self._recommendations_http_client),
            method="POST",
            path="/papers/",
            response_model=(SemanticScholarRecommendationsResponse),
            params={
                "limit": limit,
                "fields": ",".join(PAPER_FIELDS),
            },
            json_body={
                "positivePaperIds": (normalized_positive_ids),
                "negativePaperIds": (normalized_negative_ids),
            },
        )

    async def close(self) -> None:
        """Close managed HTTP clients."""

        await self._graph_http_client.close()

        if self._recommendations_http_client is not self._graph_http_client:
            await self._recommendations_http_client.close()

    async def _request_model(
        self,
        *,
        client: AsyncHttpClient,
        method: str,
        path: str,
        response_model: type[ResponseModelT],
        params: Mapping[
            str,
            str | int | float | bool | None,
        ]
        | None = None,
        json_body: Any | None = None,
    ) -> ResponseModelT:
        """Execute one request with bounded retries."""

        attempts = self._settings.semantic_scholar_max_retry_attempts

        for attempt_number in range(
            1,
            attempts + 1,
        ):
            try:
                response = await client.request(
                    method=method,
                    url=path,
                    params=params,
                    headers=self._build_headers(),
                    json=json_body,
                )

            except httpx.TimeoutException as exc:
                if attempt_number >= attempts:
                    raise ProviderTransportError(
                        provider=_PROVIDER,
                        code=("semantic_scholar_timeout"),
                        message=("Semantic Scholar request timed out."),
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
                        code=("semantic_scholar_transport_error"),
                        message=("Semantic Scholar could not be reached."),
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

            return self._parse_response(
                response=response,
                response_model=response_model,
            )

        raise ProviderTransportError(
            provider=_PROVIDER,
            code=("semantic_scholar_retry_exhausted"),
            message=("Semantic Scholar request retries were exhausted."),
            retryable=True,
        )

    def _parse_response(
        self,
        *,
        response: httpx.Response,
        response_model: type[ResponseModelT],
    ) -> ResponseModelT:
        """Parse success or raise a normalized provider error."""

        if not response.is_success:
            self._raise_for_error_response(response)

        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderResponseError(
                provider=_PROVIDER,
                code=("semantic_scholar_invalid_json"),
                message=("Semantic Scholar returned invalid JSON."),
                retryable=False,
                status_code=response.status_code,
            ) from exc

        try:
            return response_model.model_validate(payload)
        except ValidationError as exc:
            logger.warning(
                "semantic_scholar_response_validation_failed",
                status_code=response.status_code,
                validation_errors=exc.errors(include_url=False),
            )

            raise ProviderResponseError(
                provider=_PROVIDER,
                code=("semantic_scholar_invalid_response"),
                message=("Semantic Scholar returned an unexpected response structure."),
                retryable=False,
                status_code=response.status_code,
            ) from exc

    def _raise_for_error_response(
        self,
        response: httpx.Response,
    ) -> NoReturn:
        """Convert an HTTP error response into a provider error."""

        error = self._parse_error_body(response)

        message = error.safe_message
        status_code = response.status_code

        if status_code in {401, 403}:
            raise ProviderAuthenticationError(
                provider=_PROVIDER,
                code=("semantic_scholar_authentication_failed"),
                message=message,
                retryable=False,
                status_code=status_code,
            )

        if status_code == 404:
            raise ProviderNotFoundError(
                provider=_PROVIDER,
                code=("semantic_scholar_not_found"),
                message=message,
                retryable=False,
                status_code=status_code,
            )

        if status_code == 429:
            raise ProviderRateLimitError(
                provider=_PROVIDER,
                code=("semantic_scholar_rate_limited"),
                message=message,
                retryable=True,
                status_code=status_code,
                retry_after_seconds=(self._retry_after_seconds(response)),
            )

        if 400 <= status_code < 500:
            raise ProviderRequestError(
                provider=_PROVIDER,
                code=("semantic_scholar_request_rejected"),
                message=message,
                retryable=False,
                status_code=status_code,
            )

        if status_code >= 500:
            raise ProviderUpstreamError(
                provider=_PROVIDER,
                code=("semantic_scholar_upstream_failure"),
                message=message,
                retryable=True,
                status_code=status_code,
            )

        raise ProviderResponseError(
            provider=_PROVIDER,
            code=("semantic_scholar_unexpected_status"),
            message=message,
            retryable=False,
            status_code=status_code,
        )

    @staticmethod
    def _parse_error_body(
        response: httpx.Response,
    ) -> SemanticScholarErrorResponse:
        """Parse a provider error body safely."""

        fallback_message = "Semantic Scholar returned an HTTP error."

        try:
            payload = response.json()
        except ValueError:
            payload = {
                "message": fallback_message,
            }

        if not isinstance(payload, dict):
            payload = {
                "message": fallback_message,
            }

        try:
            return SemanticScholarErrorResponse.model_validate(payload)
        except ValidationError:
            return SemanticScholarErrorResponse(
                message=fallback_message,
                code=response.status_code,
            )

    def _build_headers(
        self,
    ) -> dict[str, str]:
        """Build headers with optional API-key authentication."""

        headers = {
            "Accept": "application/json",
        }

        api_key = self._settings.semantic_scholar_api_key_value()

        if api_key is not None:
            headers["x-api-key"] = api_key

        return headers

    async def _sleep_before_retry(
        self,
        *,
        attempt_number: int,
        response: httpx.Response | None,
    ) -> None:
        """Sleep using Retry-After or exponential backoff."""

        retry_after = (
            self._retry_after_seconds(response) if response is not None else None
        )

        if retry_after is None:
            minimum = self._settings.semantic_scholar_retry_min_seconds
            maximum = self._settings.semantic_scholar_retry_max_seconds

            exponential_delay = minimum * (2 ** (attempt_number - 1))

            bounded_delay = min(
                exponential_delay,
                maximum,
            )

            jitter_limit = min(
                1.0,
                bounded_delay * 0.25,
            )

            retry_after = bounded_delay + random.uniform(
                0.0,
                jitter_limit,
            )

        retry_after = min(
            retry_after,
            self._settings.semantic_scholar_retry_max_seconds,
        )

        logger.warning(
            "semantic_scholar_request_retrying",
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
            return max(
                float(stripped_value),
                0.0,
            )
        except ValueError:
            pass

        try:
            retry_datetime = email.utils.parsedate_to_datetime(stripped_value)
        except (
            TypeError,
            ValueError,
            OverflowError,
        ):
            return None

        if retry_datetime.tzinfo is None:
            retry_datetime = retry_datetime.replace(tzinfo=UTC)

        seconds = (retry_datetime - datetime.now(UTC)).total_seconds()

        return max(
            seconds,
            0.0,
        )

    @staticmethod
    def _build_year_filter(
        *,
        year_from: int | None,
        year_to: int | None,
    ) -> str | None:
        """Build Semantic Scholar's year-filter syntax."""

        if year_from is None and year_to is None:
            return None

        if year_from is not None and year_to is not None:
            return f"{year_from}-{year_to}"

        if year_from is not None:
            return f"{year_from}-"

        return f"-{year_to}"

    @staticmethod
    def _validate_paper_id(
        paper_id: str,
    ) -> str:
        """Validate and normalize a paper identifier."""

        normalized = paper_id.strip()

        if not normalized:
            raise ProviderRequestError(
                provider=_PROVIDER,
                code="invalid_paper_id",
                message=("Paper identifier cannot be empty."),
                retryable=False,
            )

        return normalized

    @classmethod
    def _normalize_paper_ids(
        cls,
        paper_ids: list[str],
    ) -> list[str]:
        """Normalize and deduplicate paper identifiers."""

        normalized: list[str] = []
        seen: set[str] = set()

        for paper_id in paper_ids:
            value = cls._validate_paper_id(paper_id)

            if value in seen:
                continue

            seen.add(value)
            normalized.append(value)

        return normalized
