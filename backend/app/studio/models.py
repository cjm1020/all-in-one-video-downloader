from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..security import normalize_url

ProjectStatus = Literal["draft", "active", "delivered"]
MAX_PROJECT_ITEMS = 500


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


class ProjectPatch(StudioModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    client: str | None = Field(None, max_length=120)
    budget_cents: int | None = Field(None, ge=0, le=1_000_000_000_000)
    due_at: datetime | None = None
    notes: str | None = Field(None, max_length=20000)
    status: ProjectStatus | None = None

    @field_validator("name", "client")
    @classmethod
    def trim_patch_labels(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value

    @field_validator("due_at")
    @classmethod
    def patch_deadline(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("截止日期需要包含时区")
        return value.astimezone(timezone.utc) if value else None


class ItemReplace(StudioModel):
    task_ids: list[str] = Field(max_length=MAX_PROJECT_ITEMS)


class RightsPatch(StudioModel):
    license: Literal["unknown", "owned", "cc0", "cc-by", "permission"]
    attribution: str = Field("", max_length=5000)
    evidence_url: str = Field("", max_length=2048)
    verified: bool = False

    @field_validator("attribution", "evidence_url")
    @classmethod
    def trim_rights(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_evidence(self):
        if self.license == "unknown" and self.verified:
            raise ValueError("未知授权不能标记为已审核")
        if self.license == "cc-by" and not self.attribution:
            raise ValueError("CC BY 素材需要填写作者、来源和许可署名")
        if self.license == "permission" and not self.evidence_url:
            raise ValueError("单独授权素材需要提供授权证据链接")
        if self.evidence_url:
            self.evidence_url = normalize_url(self.evidence_url)
        return self


class WorkflowCreate(StudioModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field("", max_length=2000)
    preset: Literal["everyday", "archive", "commute", "audio"] = "everyday"
    collection_id: str = Field("inbox", min_length=1, max_length=80)
    tags: list[str] = Field(default_factory=list, max_length=12)
    rate_limit: int = Field(0, ge=0, le=100000)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("工作流名称不能为空")
        return value

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, values: list[str]) -> list[str]:
        if any(len(value) > 200 for value in values):
            raise ValueError("标签内容过长")
        return list(dict.fromkeys(value.strip()[:30] for value in values if value.strip()))


class WorkflowRun(StudioModel):
    urls: list[str] = Field(min_length=1, max_length=100)
    project_id: str | None = Field(None, max_length=80)

    @field_validator("urls")
    @classmethod
    def bound_urls(cls, values: list[str]) -> list[str]:
        if any(len(url) > 2048 for url in values):
            raise ValueError("链接不能超过 2048 字符")
        return values
