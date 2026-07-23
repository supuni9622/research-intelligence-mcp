"""Tests for structured tool/provider/cache/HTTP metrics."""

from __future__ import annotations

import pytest

from research_intelligence_mcp.infrastructure.cache.base import CacheStats
from research_intelligence_mcp.infrastructure.observability.metrics import (
    METRICS_REGISTRY,
    record_provider_call,
    record_provider_results,
    record_tool_call,
    refresh_cache_gauges,
    render_metrics,
)


def _sample(name: str, labels: dict[str, str]) -> float | None:
    return METRICS_REGISTRY.get_sample_value(name, labels)


def test_record_tool_call_records_success() -> None:
    """A successful tool call should increment the success counter."""

    before = (
        _sample(
            "mcp_tool_requests_total",
            {"tool": "unit_test_tool_success", "status": "success"},
        )
        or 0.0
    )

    with record_tool_call("unit_test_tool_success"):
        pass

    after = _sample(
        "mcp_tool_requests_total",
        {"tool": "unit_test_tool_success", "status": "success"},
    )

    assert after == before + 1.0


def test_record_tool_call_records_failure_and_reraises() -> None:
    """A failing tool call should increment failure counters and reraise."""

    before_failures = (
        _sample(
            "mcp_tool_failures_total",
            {"tool": "unit_test_tool_failure", "error_type": "ValueError"},
        )
        or 0.0
    )

    with pytest.raises(ValueError, match="boom"):
        with record_tool_call("unit_test_tool_failure"):
            raise ValueError("boom")

    after_failures = _sample(
        "mcp_tool_failures_total",
        {"tool": "unit_test_tool_failure", "error_type": "ValueError"},
    )

    assert after_failures == before_failures + 1.0

    status_count = _sample(
        "mcp_tool_requests_total",
        {"tool": "unit_test_tool_failure", "status": "failure"},
    )

    assert status_count == 1.0


def test_record_provider_call_records_success_and_duration() -> None:
    """A successful provider call should be recorded with zero-or-more duration."""

    with record_provider_call("unit_test_provider", "search"):
        pass

    requests = _sample(
        "provider_requests_total",
        {
            "provider": "unit_test_provider",
            "operation": "search",
            "status": "success",
        },
    )

    assert requests == 1.0

    duration_count = _sample(
        "provider_request_duration_seconds_count",
        {
            "provider": "unit_test_provider",
            "operation": "search",
            "status": "success",
        },
    )

    assert duration_count == 1.0


def test_record_provider_call_records_failure() -> None:
    """A failing provider call should record a normalized error type."""

    with pytest.raises(RuntimeError):
        with record_provider_call("unit_test_provider", "get_paper"):
            raise RuntimeError("upstream unavailable")

    failures = _sample(
        "provider_failures_total",
        {
            "provider": "unit_test_provider",
            "operation": "get_paper",
            "error_type": "RuntimeError",
        },
    )

    assert failures == 1.0


def test_record_provider_results_increments_by_count() -> None:
    """Provider result counts should accumulate by the reported amount."""

    before = (
        _sample(
            "provider_results_total",
            {"provider": "unit_test_provider", "operation": "search_results"},
        )
        or 0.0
    )

    record_provider_results("unit_test_provider", "search_results", 3)

    after = _sample(
        "provider_results_total",
        {"provider": "unit_test_provider", "operation": "search_results"},
    )

    assert after == before + 3.0


def test_record_provider_results_ignores_zero() -> None:
    """Zero results should not create spurious observations."""

    before = _sample(
        "provider_results_total",
        {"provider": "unit_test_provider", "operation": "empty_results"},
    )

    record_provider_results("unit_test_provider", "empty_results", 0)

    after = _sample(
        "provider_results_total",
        {"provider": "unit_test_provider", "operation": "empty_results"},
    )

    assert after == before


def test_refresh_cache_gauges_mirrors_stats_snapshot() -> None:
    """Cache gauges should exactly mirror the provided statistics snapshot."""

    stats = CacheStats(
        hits=5,
        misses=2,
        writes=7,
        evictions=1,
        expirations=0,
        current_size=6,
        max_size=100,
    )

    refresh_cache_gauges(cache="unit_test_cache", stats=stats)

    assert _sample("cache_hits_total", {"cache": "unit_test_cache"}) == 5.0
    assert _sample("cache_misses_total", {"cache": "unit_test_cache"}) == 2.0
    assert _sample("cache_writes_total", {"cache": "unit_test_cache"}) == 7.0
    assert _sample("cache_evictions_total", {"cache": "unit_test_cache"}) == 1.0
    assert _sample("cache_expirations_total", {"cache": "unit_test_cache"}) == 0.0
    assert _sample("cache_current_entries", {"cache": "unit_test_cache"}) == 6.0


def test_render_metrics_returns_prometheus_text_format() -> None:
    """Rendered metrics should include the Prometheus HELP/TYPE preamble."""

    with record_tool_call("unit_test_render_tool"):
        pass

    payload = render_metrics().decode("utf-8")

    assert "# HELP mcp_tool_requests_total" in payload
    assert "# TYPE mcp_tool_requests_total counter" in payload
    assert 'tool="unit_test_render_tool"' in payload
