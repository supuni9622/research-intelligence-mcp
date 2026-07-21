"""Deterministic keys for provider search and paper caches."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from research_intelligence_mcp.domain.enums import (
    ProviderName,
)
from research_intelligence_mcp.domain.requests import (
    SearchRequest,
)


def build_search_cache_key(
    *,
    provider: ProviderName,
    request: SearchRequest,
) -> str:
    """Build a deterministic key for one provider search request."""

    payload = {
        "provider": provider.value,
        "query": request.query,
        "limit": request.limit,
        "offset": request.offset,
        "year_from": request.year_from,
        "year_to": request.year_to,
        "fields_of_study": list(request.fields_of_study),
        "open_access_only": request.open_access_only,
        "sort": request.sort.value,
    }

    digest = _hash_payload(payload)

    return f"search:{provider.value}:{digest}"


def build_paper_cache_key(
    *,
    provider: ProviderName,
    paper_id: str,
) -> str:
    """Build a deterministic key for one provider paper identifier."""

    normalized_paper_id = " ".join(paper_id.split()).casefold()

    payload = {
        "provider": provider.value,
        "paper_id": normalized_paper_id,
    }

    digest = _hash_payload(payload)

    return f"paper:{provider.value}:{digest}"


def _hash_payload(
    payload: dict[str, Any],
) -> str:
    """Serialize and hash a cache-key payload."""

    serialized = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )

    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
