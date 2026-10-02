from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ProjectStatus = Literal["draft", "active", "delivered"]


class StudioModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectCreate(StudioModel):
    name: str = Field(min_length=1, max_length=120)
    client: str = Field("", max_length=120)
    budget_cents: int = Field(0, ge=0, le=1_000_000_000_000)
    due_at: datetime | None = None
    notes: str = Field("", max_length=20000)

    @field_validator("name", "client")
    @classmethod
    def trim_labels(cls, value: str, info) -> str:
        value = value.strip()
        if info.field_name == "name" and not value:
            raise ValueError("项目名称不能为空")
        return value

    @field_validator("due_at")
    @classmethod
    def aware_deadline(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("截止日期需要包含时区")
        return value.astimezone(timezone.utc) if value else None
