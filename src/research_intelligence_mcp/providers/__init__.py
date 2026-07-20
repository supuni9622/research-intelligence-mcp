"""Academic-paper provider integrations."""

from research_intelligence_mcp.providers.base import (
    PaperProvider,
)
from research_intelligence_mcp.providers.errors import (
    ProviderAuthenticationError,
    ProviderError,
    ProviderNotFoundError,
    ProviderRateLimitError,
    ProviderRequestError,
    ProviderResponseError,
    ProviderTransportError,
    ProviderUpstreamError,
)
from research_intelligence_mcp.providers.semantic_scholar import (
    SemanticScholarClient,
    SemanticScholarMapper,
    SemanticScholarProvider,
    create_semantic_scholar_client,
    create_semantic_scholar_provider,
)

__all__ = [
    "PaperProvider",
    "ProviderAuthenticationError",
    "ProviderError",
    "ProviderNotFoundError",
    "ProviderRateLimitError",
    "ProviderRequestError",
    "ProviderResponseError",
    "ProviderTransportError",
    "ProviderUpstreamError",
    "SemanticScholarClient",
    "SemanticScholarMapper",
    "SemanticScholarProvider",
    "create_semantic_scholar_client",
    "create_semantic_scholar_provider",
]
