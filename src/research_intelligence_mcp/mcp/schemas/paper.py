from pydantic import BaseModel, ConfigDict, Field

from research_intelligence_mcp.domain.enums import ProviderName


class GetPaperInput(
    BaseModel,
):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    provider: ProviderName = Field(
        description="Provider used to retrieve the paper.",
    )

    paper_id: str = Field(
        min_length=1,
        max_length=500,
        description="Provider paper identifier.",
    )