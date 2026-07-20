"""Normalized errors raised by external research providers."""

from __future__ import annotations

from typing import Any

from research_intelligence_mcp.domain.enums import ProviderName


class ProviderError(Exception):
    """Base exception for normalized provider failures."""

    def __init__(
        self,
        *,
        provider: ProviderName,
        code: str,
        message: str,
        retryable: bool,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a normalized provider error."""

        super().__init__(message)

        self.provider = provider
        self.code = code
        self.message = message
        self.retryable = retryable
        self.status_code = status_code
        self.details = details or {}

    def __str__(self) -> str:
        """Return a safe diagnostic representation."""

        return f"{self.provider.value}: {self.code}: {self.message}"


class ProviderAuthenticationError(ProviderError):
    """Provider authentication or authorization failed."""


class ProviderNotFoundError(ProviderError):
    """The requested provider resource was not found."""


class ProviderRateLimitError(ProviderError):
    """The provider rejected a request due to rate limiting."""

    def __init__(
        self,
        *,
        provider: ProviderName,
        code: str,
        message: str,
        retryable: bool,
        status_code: int | None = None,
        retry_after_seconds: float | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a normalized provider rate-limit error."""

        super().__init__(
            provider=provider,
            code=code,
            message=message,
            retryable=retryable,
            status_code=status_code,
            details=details,
        )

        self.retry_after_seconds = retry_after_seconds


class ProviderRequestError(ProviderError):
    """The provider rejected an invalid client request."""


class ProviderTransportError(ProviderError):
    """A network or transport failure prevented the request."""


class ProviderUpstreamError(ProviderError):
    """The provider returned a temporary upstream failure."""


class ProviderResponseError(ProviderError):
    """The provider returned malformed or unexpected response data."""
