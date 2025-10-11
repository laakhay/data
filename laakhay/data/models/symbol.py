"""Trading symbol data model."""

from pydantic import BaseModel, ConfigDict, Field


class Symbol(BaseModel):
    """Trading symbol information."""

    symbol: str = Field(..., min_length=1)
    base_asset: str = Field(..., min_length=1)
    quote_asset: str = Field(..., min_length=1)

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)
