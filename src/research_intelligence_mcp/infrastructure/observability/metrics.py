"""Structured, low-cardinality metrics for MCP tools, providers, and caches.

Implements the "Structured Metrics" milestone of
``docs/remote_mcp_deployment_prd.md``. Metrics are collected in a dedicated
:class:`~prometheus_client.CollectorRegistry` (rather than the global default
registry) so that repeated test-suite imports and dependency rebuilds never
raise duplicate-timeseries registration errors.

Label values are restricted to fixed, bounded vocabularies (tool names,
provider names, operation names, HTTP status codes, and cache names) and must
never include request-scoped or user-controlled values such as queries,
paper identifiers, correlation IDs, or exception messages. See the
"Prohibited Labels" section of the deployment PRD.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from time import perf_counter

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

from research_intelligence_mcp.infrastructure.cache.base import CacheStats

METRICS_REGISTRY = CollectorRegistry()

# MCP tool metrics

MCP_TOOL_REQUESTS_TOTAL = Counter(
    "mcp_tool_requests_total",
    "Total MCP tool invocations.",
    ["tool", "status"],
    registry=METRICS_REGISTRY,
)

MCP_TOOL_DURATION_SECONDS = Histogram(
    "mcp_tool_duration_seconds",
    "MCP tool call duration in seconds.",
    ["tool", "status"],
    registry=METRICS_REGISTRY,
)

MCP_TOOL_FAILURES_TOTAL = Counter(
    "mcp_tool_failures_total",
    "Total MCP tool call failures.",
    ["tool", "error_type"],
    registry=METRICS_REGISTRY,
)

# Research-provider metrics

PROVIDER_REQUESTS_TOTAL = Counter(
    "provider_requests_total",
    "Total research-provider requests.",
    ["provider", "operation", "status"],
    registry=METRICS_REGISTRY,
)

PROVIDER_REQUEST_DURATION_SECONDS = Histogram(
    "provider_request_duration_seconds",
    "Research-provider request duration in seconds.",
    ["provider", "operation", "status"],
    registry=METRICS_REGISTRY,
)

PROVIDER_FAILURES_TOTAL = Counter(
    "provider_failures_total",
    "Total research-provider request failures.",
    ["provider", "operation", "error_type"],
    registry=METRICS_REGISTRY,
)

PROVIDER_RESULTS_TOTAL = Counter(
    "provider_results_total",
    "Total items returned by successful research-provider requests.",
    ["provider", "operation"],
    registry=METRICS_REGISTRY,
)

# Cache metrics, mirrored from existing AsyncBoundedTTLCache statistics.
#
# Gauge (not Counter) is deliberate: values are set from an already
# cumulative, monotonically-tracked snapshot (CacheStats) rather than
# incremented per event, and current_size must be able to decrease.

CACHE_HITS_TOTAL = Gauge(
    "cache_hits_total",
    "Total cache hits.",
    ["cache"],
    registry=METRICS_REGISTRY,
)

CACHE_MISSES_TOTAL = Gauge(
    "cache_misses_total",
    "Total cache misses.",
    ["cache"],
    registry=METRICS_REGISTRY,
)

CACHE_WRITES_TOTAL = Gauge(
    "cache_writes_total",
    "Total cache writes.",
    ["cache"],
    registry=METRICS_REGISTRY,
)

CACHE_EVICTIONS_TOTAL = Gauge(
    "cache_evictions_total",
    "Total cache LRU evictions.",
    ["cache"],
    registry=METRICS_REGISTRY,
)

CACHE_EXPIRATIONS_TOTAL = Gauge(
    "cache_expirations_total",
    "Total cache TTL expirations.",
    ["cache"],
    registry=METRICS_REGISTRY,
)

CACHE_CURRENT_ENTRIES = Gauge(
    "cache_current_entries",
    "Current number of live cache entries.",
    ["cache"],
    registry=METRICS_REGISTRY,
)

# HTTP transport metrics (streamable-http only)

MCP_HTTP_REQUESTS_TOTAL = Counter(
    "mcp_http_requests_total",
    "Total HTTP requests handled by the streamable-http transport.",
    ["method", "route", "status_code"],
    registry=METRICS_REGISTRY,
)

MCP_HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "mcp_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ["method", "route", "status_code"],
    registry=METRICS_REGISTRY,
)

MCP_HTTP_IN_FLIGHT_REQUESTS = Gauge(
    "mcp_http_in_flight_requests",
    "Number of HTTP requests currently being handled.",
    ["method", "route"],
    registry=METRICS_REGISTRY,
)


@contextmanager
def record_tool_call(tool_name: str) -> Generator[None]:
    """Record a request/duration/failure metric triple for one tool call.

    Reraises any exception raised inside the scope after recording it, so
    this composes transparently with the existing ``correlation_scope``
    context manager without changing tool error behavior.
    """

    start = perf_counter()
    status = "success"
    error_type: str | None = None

    try:
        yield
    except Exception as exc:
        status = "failure"
        error_type = type(exc).__name__
        raise
    finally:
        duration = perf_counter() - start

        MCP_TOOL_REQUESTS_TOTAL.labels(tool=tool_name, status=status).inc()
        MCP_TOOL_DURATION_SECONDS.labels(tool=tool_name, status=status).observe(
            duration
        )

        if error_type is not None:
            MCP_TOOL_FAILURES_TOTAL.labels(
                tool=tool_name,
                error_type=error_type,
            ).inc()


@contextmanager
def record_provider_call(
    provider: str,
    operation: str,
) -> Generator[None]:
    """Record a request/duration/failure metric triple for one provider call.

    Callers should wrap only the actual upstream provider invocation (not
    cache-hit paths), so ``provider_requests_total`` reflects real requests.
    """

    start = perf_counter()
    status = "success"
    error_type: str | None = None

    try:
        yield
    except Exception as exc:
        status = "failure"
        error_type = type(exc).__name__
        raise
    finally:
        duration = perf_counter() - start

        PROVIDER_REQUESTS_TOTAL.labels(
            provider=provider,
            operation=operation,
            status=status,
        ).inc()
        PROVIDER_REQUEST_DURATION_SECONDS.labels(
            provider=provider,
            operation=operation,
            status=status,
        ).observe(duration)

        if error_type is not None:
            PROVIDER_FAILURES_TOTAL.labels(
                provider=provider,
                operation=operation,
                error_type=error_type,
            ).inc()


def record_provider_results(
    provider: str,
    operation: str,
    count: int,
) -> None:
    """Record the number of items returned by a successful provider call."""

    if count > 0:
        PROVIDER_RESULTS_TOTAL.labels(provider=provider, operation=operation).inc(count)


def refresh_cache_gauges(
    *,
    cache: str,
    stats: CacheStats,
) -> None:
    """Mirror a cache's current statistics snapshot into the gauges above."""

    CACHE_HITS_TOTAL.labels(cache=cache).set(stats.hits)
    CACHE_MISSES_TOTAL.labels(cache=cache).set(stats.misses)
    CACHE_WRITES_TOTAL.labels(cache=cache).set(stats.writes)
    CACHE_EVICTIONS_TOTAL.labels(cache=cache).set(stats.evictions)
    CACHE_EXPIRATIONS_TOTAL.labels(cache=cache).set(stats.expirations)
    CACHE_CURRENT_ENTRIES.labels(cache=cache).set(stats.current_size)


def render_metrics() -> bytes:
    """Render every registered metric in Prometheus text-exposition format."""

    return generate_latest(METRICS_REGISTRY)


METRICS_CONTENT_TYPE = CONTENT_TYPE_LATEST
