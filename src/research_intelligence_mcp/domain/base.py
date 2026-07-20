"""Shared configuration for canonical domain models."""

from pydantic import BaseModel, ConfigDict


class DomainModel(BaseModel):
    """Base class for immutable provider-neutral domain models."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        validate_default=True,
        use_enum_values=False,
    )
