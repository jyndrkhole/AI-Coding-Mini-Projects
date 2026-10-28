"""Structured records shared by the specialists and the fact checker."""

from __future__ import annotations

from pydantic import BaseModel, Field


class NumericClaim(BaseModel):
    metric: str
    scope: str
    value: float | int | None


class Quote(BaseModel):
    response_id: str
    comment: str
    theme: str | None = None
    score: int | None = None


class SpecialistStatus(BaseModel):
    agent: str
    available: bool
    tools_used: list[str] = Field(default_factory=list)
    error: str | None = None
