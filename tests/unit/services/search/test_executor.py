"""Tests for concurrent provider execution."""

from __future__ import annotations

import pytest
from tests.unit.services.search.helpers import (
    StubProvider,
    build_paper,
    build_provider_error,
    build_request,
    build_result,
)

from research_intelligence_mcp.domain.enums import ProviderName
from research_intelligence_mcp.services.search.executor import (
    ProviderExecutor,
)
from research_intelligence_mcp.services.search.provider_registry import (
    ProviderRegistry,
)


@pytest.mark.asyncio
async def test_executes_all_requested_providers() -> None:
    """Every requested provider should receive the request."""

    request = build_request()

    semantic_paper = build_paper(
        title="Semantic Scholar Paper",
        source=ProviderName.SEMANTIC_SCHOLAR,
        corpus_id=1,
    )
    arxiv_paper = build_paper(
        title="arXiv Paper",
        source=ProviderName.ARXIV,
        arxiv_id="2401.00001",
    )

    semantic_scholar = StubProvider(
        name=ProviderName.SEMANTIC_SCHOLAR,
        result=build_result(
            provider=ProviderName.SEMANTIC_SCHOLAR,
            papers=(semantic_paper,),
        ),
    )
    arxiv = StubProvider(
        name=ProviderName.ARXIV,
        result=build_result(
            provider=ProviderName.ARXIV,
            papers=(arxiv_paper,),
        ),
    )

    executor = ProviderExecutor(
        registry=ProviderRegistry(
            providers=(
                semantic_scholar,
                arxiv,
            )
        )
    )

    results = await executor.execute(request)

    assert len(results) == 2
    assert semantic_scholar.requests == [request]
    assert arxiv.requests == [request]
    assert results[0].providers_succeeded == (ProviderName.SEMANTIC_SCHOLAR,)
    assert results[1].providers_succeeded == (ProviderName.ARXIV,)


@pytest.mark.asyncio
async def test_isolates_normalized_provider_failure() -> None:
    """One ProviderError should not discard other provider results."""

    request = build_request()

    semantic_paper = build_paper(
        title="Available Paper",
        source=ProviderName.SEMANTIC_SCHOLAR,
        corpus_id=10,
    )

    semantic_scholar = StubProvider(
        name=ProviderName.SEMANTIC_SCHOLAR,
        result=build_result(
            provider=ProviderName.SEMANTIC_SCHOLAR,
            papers=(semantic_paper,),
        ),
    )
    arxiv = StubProvider(
        name=ProviderName.ARXIV,
        error=build_provider_error(
            provider=ProviderName.ARXIV,
        ),
    )

    executor = ProviderExecutor(
        registry=ProviderRegistry(
            providers=(
                semantic_scholar,
                arxiv,
            )
        )
    )

    results = await executor.execute(request)

    assert len(results) == 2
    assert results[0].papers == (semantic_paper,)

    failed_result = results[1]

    assert failed_result.papers == ()
    assert failed_result.providers_requested == (ProviderName.ARXIV,)
    assert failed_result.providers_succeeded == ()
    assert len(failed_result.failures) == 1
    assert failed_result.failures[0].provider == ProviderName.ARXIV
    assert failed_result.failures[0].code == "provider_unavailable"
    assert failed_result.failures[0].retryable is True


@pytest.mark.asyncio
async def test_normalizes_unexpected_provider_exception() -> None:
    """Unexpected failures should become safe canonical failures."""

    request = build_request(providers=(ProviderName.ARXIV,))

    arxiv = StubProvider(
        name=ProviderName.ARXIV,
        error=RuntimeError("Internal secret should not escape."),
    )

    executor = ProviderExecutor(registry=ProviderRegistry(providers=(arxiv,)))

    results = await executor.execute(request)

    assert len(results) == 1

    failure = results[0].failures[0]

    assert failure.provider == ProviderName.ARXIV
    assert failure.code == "unexpected_provider_error"
    assert failure.retryable is False
    assert "Internal secret" not in failure.message


@pytest.mark.asyncio
async def test_executes_only_selected_provider() -> None:
    """Unselected providers should not be called."""

    request = build_request(providers=(ProviderName.ARXIV,))

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

    executor = ProviderExecutor(
        registry=ProviderRegistry(
            providers=(
                semantic_scholar,
                arxiv,
            )
        )
    )

    results = await executor.execute(request)

    assert len(results) == 1
    assert semantic_scholar.requests == []
    assert arxiv.requests == [request]
