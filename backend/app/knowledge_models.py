"""Inputs for source-backed knowledge tools; no external AI is required."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class KnowledgeInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class MarkerCreate(KnowledgeInput):
    position: float = Field(ge=0, le=86400, allow_inf_nan=False)
    label: str = Field(min_length=1, max_length=120)
    notes: str = Field(default="", max_length=5000)
    color: Literal["sage", "peach", "lavender", "sky"] = "sage"


class CardCreate(KnowledgeInput):
    question: str = Field(min_length=1, max_length=2000)
    answer: str = Field(min_length=1, max_length=5000)


class ReviewInput(KnowledgeInput):
    rating: Literal["again", "good", "easy"]


class SearchInput(KnowledgeInput):
    q: str = Field(min_length=1, max_length=100)
    limit: int = Field(default=20, ge=1, le=100)

    @field_validator("q")
    @classmethod
    def meaningful_query(cls, value):
        if not value.strip():
            raise ValueError("请输入要检索的字幕关键词")
        return value
