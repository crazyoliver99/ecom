"""Request/response schemas for the HTTP API."""

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

CandidateStatus = Literal["new", "collecting", "analyzed", "decided"]


def _require_non_blank(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("must not be blank or whitespace-only")
    return stripped


class CandidateCreate(BaseModel):
    name: str = Field(max_length=500)
    niche: str | None = None
    notes: str | None = None
    seed_urls: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        return _require_non_blank(value)


class CandidateUpdate(BaseModel):
    """PATCH body — only the provided fields are changed."""

    name: str | None = Field(default=None, max_length=500)
    niche: str | None = None
    notes: str | None = None
    seed_urls: list[str] | None = None
    status: CandidateStatus | None = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str | None) -> str | None:
        return None if value is None else _require_non_blank(value)


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    niche: str | None
    notes: str | None
    seed_urls: list[str]
    status: str
    created_at: datetime
    updated_at: datetime


class CandidateList(BaseModel):
    items: list[CandidateOut]
    total: int
    limit: int
    offset: int


class ObservationCreate(BaseModel):
    payload: dict
    source_url: HttpUrl | None = None
    fetched_at: datetime | None = None

    @field_validator("fetched_at")
    @classmethod
    def fetched_at_aware_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError(
                "must include a timezone (e.g. 2026-07-11T12:00:00Z); naive timestamps "
                "are ambiguous evidence"
            )
        return value.astimezone(UTC)


class ObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID | None
    source_id: uuid.UUID
    run_id: uuid.UUID | None
    observation_type: str
    payload: dict
    source_url: str | None
    fetched_at: datetime
    created_at: datetime


class ObservationList(BaseModel):
    items: list[ObservationOut]
    total: int
    limit: int
    offset: int
