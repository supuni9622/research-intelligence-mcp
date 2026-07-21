from typing import cast

import pytest

from research_intelligence_mcp.domain.enums import (
    ProviderName,
)
from research_intelligence_mcp.domain.identifiers import (
    PaperIdentifiers,
)
from research_intelligence_mcp.domain.models import (
    Paper,
)
from research_intelligence_mcp.mcp.schemas.paper import (
    GetPaperInput,
)
from research_intelligence_mcp.mcp.tools.paper import (
    execute_get_paper,
)


class StubProvider:
    name = ProviderName.ARXIV

    async def get_paper(
        self,
        paper_id: str,
    ) -> Paper:
        return Paper(
            identifiers=PaperIdentifiers(
                arxiv_id=paper_id,
            ),
            title="Test Paper",
            sources=(ProviderName.ARXIV,),
        )


class StubRegistry:
    def get(
        self,
        provider: ProviderName,
    ):
        return StubProvider()


class Dependencies:
    provider_registry = StubRegistry()


@pytest.mark.asyncio
async def test_execute_get_paper() -> None:
    result = await execute_get_paper(
        paper_input=GetPaperInput(
            provider=ProviderName.ARXIV,
            paper_id="2501.12345",
        ),
        dependencies=cast(
            object,
            Dependencies(),
        ),
    )

    assert result.title == "Test Paper"

    assert (
        result.identifiers.arxiv_id
        == "2501.12345"
    )