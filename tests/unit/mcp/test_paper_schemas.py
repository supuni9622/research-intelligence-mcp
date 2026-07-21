import pytest
from pydantic import ValidationError

from research_intelligence_mcp.domain.enums import (
    ProviderName,
)
from research_intelligence_mcp.mcp.schemas.paper import (
    GetPaperInput,
)


def test_valid_input() -> None:
    model = GetPaperInput(
        provider=ProviderName.ARXIV,
        paper_id="2501.12345",
    )

    assert model.paper_id == "2501.12345"


def test_empty_id() -> None:
    with pytest.raises(
        ValidationError,
    ):
        GetPaperInput(
            provider=ProviderName.ARXIV,
            paper_id="",
        )