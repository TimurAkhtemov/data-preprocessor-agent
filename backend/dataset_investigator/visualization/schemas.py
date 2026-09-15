from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChartSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["histogram", "box", "bar", "scatter", "line", "missingness"]
    x: str | None = None
    y: str | None = None
    color: str | None = None
    title: str = Field(min_length=1, max_length=200)
    top_n: int | None = Field(default=None, ge=1)

    @field_validator("top_n")
    @classmethod
    def clamp_top_n(cls, value):
        return min(value, 30) if value is not None else None
