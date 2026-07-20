"""Registry for canonical research providers."""

from __future__ import annotations

from collections.abc import Iterable

from research_intelligence_mcp.domain.enums import ProviderName
from research_intelligence_mcp.providers.base import PaperProvider


class ProviderRegistry:
    """Store and resolve configured paper providers."""

    def __init__(
        self,
        providers: Iterable[PaperProvider],
    ) -> None:
        """Register the supplied providers."""

        self._providers: dict[ProviderName, PaperProvider] = {}

        for provider in providers:
            if provider.name in self._providers:
                raise ValueError(f"Provider already registered: {provider.name.value}")

            self._providers[provider.name] = provider

    def get(
        self,
        provider_name: ProviderName,
    ) -> PaperProvider:
        """Return one registered provider."""

        try:
            return self._providers[provider_name]
        except KeyError as exc:
            raise ValueError(
                f"Provider is not registered: {provider_name.value}"
            ) from exc

    def list(self) -> tuple[PaperProvider, ...]:
        """Return all registered providers."""

        return tuple(self._providers.values())

    def names(self) -> tuple[ProviderName, ...]:
        """Return all registered provider identifiers."""

        return tuple(self._providers)

    def exists(
        self,
        provider_name: ProviderName,
    ) -> bool:
        """Return whether a provider is registered."""

        return provider_name in self._providers
