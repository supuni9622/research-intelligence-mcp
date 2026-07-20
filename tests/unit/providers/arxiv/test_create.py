"""Tests for arXiv infrastructure and provider composition."""

from __future__ import annotations

import pytest

from research_intelligence_mcp.config.settings import Settings
from research_intelligence_mcp.providers.arxiv.client import ArxivClient
from research_intelligence_mcp.providers.arxiv.create import (
    create_arxiv_client,
    create_arxiv_provider,
)
from research_intelligence_mcp.providers.arxiv.provider import ArxivProvider


@pytest.mark.asyncio
async def test_create_arxiv_client() -> None:
    settings = Settings(_env_file=None)
    client = create_arxiv_client(settings)

    try:
        assert isinstance(client, ArxivClient)
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_create_arxiv_provider() -> None:
    settings = Settings(_env_file=None)
    provider = create_arxiv_provider(settings)

    try:
        assert isinstance(provider, ArxivProvider)
        assert provider.name.value == "arxiv"
    finally:
        await provider.close()
