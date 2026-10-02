from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Preset = Literal["everyday", "archive", "commute", "audio"]


class InspectRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2048)


class CreateTasks(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=30)
    preset: Preset = "everyday"
    collection_id: str = "inbox"
    scheduled_at: datetime | None = None
    clip_start: float | None = Field(None, ge=0, le=86400)
    clip_end: float | None = Field(None, gt=0, le=86400)
    rate_limit: int = Field(0, ge=0, le=100000)

    @field_validator("urls")
    @classmethod
    def validate_urls(cls, values: list[str]) -> list[str]:
        if any(len(v) > 2048 for v in values):
            raise ValueError("链接不能超过 2048 字符")
        return values

    @field_validator("scheduled_at")
    @classmethod
    def validate_time(cls, value: datetime | None) -> datetime | None:
        if value and value.tzinfo is None:
            raise ValueError("预约时间需要包含时区")
        return value.astimezone(timezone.utc) if value else None

    @model_validator(mode="after")
    def validate_clip(self):
        if (self.clip_start is None) != (self.clip_end is None):
            raise ValueError("请同时填写片段开始和结束时间")
        if self.clip_end is not None and self.clip_end <= self.clip_start:
            raise ValueError("结束时间必须晚于开始时间")
        return self


class TaskPatch(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    collection_id: str | None = None
    favorite: bool | None = None
    tags: list[str] | None = Field(None, max_length=12)
    notes: str | None = Field(None, max_length=20000)

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, tags: list[str] | None) -> list[str] | None:
        if tags is None:
            return None
        return list(dict.fromkeys(t.strip()[:30] for t in tags if t.strip()))


class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    color: Literal["sage", "peach", "lavender", "sky"] = "sage"


class TranscriptRequest(BaseModel):
    text: str = Field(min_length=1, max_length=250000)


class SummaryRequest(BaseModel):
    mode: Literal["local", "ai"] = "local"


class SettingsUpdate(BaseModel):
    default_preset: Preset = "everyday"
    rate_limit: int = Field(0, ge=0, le=100000)
    storage_limit_gb: float = Field(10, ge=0.1, le=10000)

