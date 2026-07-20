"""Tests for the provider registry."""

from __future__ import annotations

import pytest
from tests.unit.services.search.helpers import (
    StubProvider,
    build_result,
)

from research_intelligence_mcp.domain.enums import ProviderName
from research_intelligence_mcp.services.search.provider_registry import (
    ProviderRegistry,
)


def test_registers_and_resolves_providers() -> None:
    """Registered providers should be retrievable by name."""

    semantic_scholar = StubProvider(
        name=ProviderName.SEMANTIC_SCHOLAR,
        result=build_result(
            provider=ProviderName.SEMANTIC_SCHOLAR,
        ),
    )
    arxiv = StubProvider(
        name=ProviderName.ARXIV,
        result=build_result(
            provider=ProviderName.ARXIV,
        ),
    )

    registry = ProviderRegistry(
        providers=(
            semantic_scholar,
            arxiv,
        )
    )

    assert registry.get(ProviderName.SEMANTIC_SCHOLAR) is semantic_scholar
    assert registry.get(ProviderName.ARXIV) is arxiv


def test_lists_registered_providers_in_registration_order() -> None:
    """Provider ordering should remain deterministic."""

    semantic_scholar = StubProvider(
        name=ProviderName.SEMANTIC_SCHOLAR,
        result=build_result(
            provider=ProviderName.SEMANTIC_SCHOLAR,
        ),
    )
    arxiv = StubProvider(
        name=ProviderName.ARXIV,
        result=build_result(
            provider=ProviderName.ARXIV,
        ),
    )

    registry = ProviderRegistry(
        providers=(
            semantic_scholar,
            arxiv,
        )
    )

    assert registry.list() == (
        semantic_scholar,
        arxiv,
    )
    assert registry.names() == (
        ProviderName.SEMANTIC_SCHOLAR,
        ProviderName.ARXIV,
    )


def test_reports_whether_provider_exists() -> None:
    """Registry membership should be queryable."""

    provider = StubProvider(
        name=ProviderName.ARXIV,
        result=build_result(
            provider=ProviderName.ARXIV,
        ),
    )

    registry = ProviderRegistry(providers=(provider,))

    assert registry.exists(ProviderName.ARXIV)
    assert not registry.exists(ProviderName.SEMANTIC_SCHOLAR)


def test_rejects_duplicate_provider_registration() -> None:
    """Only one provider implementation may exist per provider name."""

    first = StubProvider(
        name=ProviderName.ARXIV,
        result=build_result(
            provider=ProviderName.ARXIV,
        ),
    )
    second = StubProvider(
        name=ProviderName.ARXIV,
        result=build_result(
            provider=ProviderName.ARXIV,
        ),
    )

    with pytest.raises(
        ValueError,
        match="Provider already registered",
    ):
        ProviderRegistry(
            providers=(
                first,
                second,
            )
        )


def test_rejects_unknown_provider_lookup() -> None:
    """Unregistered providers should fail clearly."""

    registry = ProviderRegistry(providers=())

    with pytest.raises(
        ValueError,
        match="Provider is not registered",
    ):
        registry.get(ProviderName.ARXIV)
