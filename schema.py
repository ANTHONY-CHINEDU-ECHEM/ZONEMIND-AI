"""Structured output contract between any reasoning backend and the rest of the agent."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ZoneCommand(BaseModel):
    heat: float = Field(description="heating setpoint in C")
    cool: float = Field(description="cooling setpoint in C")
    lockout: bool = Field(default=False, description="lock out mechanical cooling, outdoor air only")


class Proposal(BaseModel):
    zones: dict[str, ZoneCommand]
    strategy: str = ""
    rationale: str = ""
    citations: list[str] = Field(default_factory=list)
