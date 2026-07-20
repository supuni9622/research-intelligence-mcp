"""Semantic Scholar paper-provider integration."""

from research_intelligence_mcp.providers.semantic_scholar.client import (
    SemanticScholarClient,
)
from research_intelligence_mcp.providers.semantic_scholar.create import (
    create_semantic_scholar_client,
    create_semantic_scholar_provider,
)
from research_intelligence_mcp.providers.semantic_scholar.mapper import (
    SemanticScholarMapper,
)
from research_intelligence_mcp.providers.semantic_scholar.provider import (
    SemanticScholarProvider,
)

__all__ = [
    "SemanticScholarClient",
    "SemanticScholarMapper",
    "SemanticScholarProvider",
    "create_semantic_scholar_client",
    "create_semantic_scholar_provider",
]
