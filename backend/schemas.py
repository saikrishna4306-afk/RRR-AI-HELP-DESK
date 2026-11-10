"""Pydantic models for strict JSON from the vision step and the answer step."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

FAULTS = ("upper_thread_breaking", "needle_breaking", "design_misalignment", "thread_nesting")
FaultOrUnknown = Literal["upper_thread_breaking", "needle_breaking", "design_misalignment", "thread_nesting", "unknown"]


class VisionResult(BaseModel):
    fault_id: FaultOrUnknown
    confidence: float = Field(ge=0.0, le=1.0)
    visible_evidence: str = Field(default="", max_length=400)


class Answer(BaseModel):
    spoken_text: str = Field(min_length=1, max_length=450)
    steps: list[str] = Field(min_length=1, max_length=6)
    safety_note: str = ""
    video_chapter_to_watch: str = ""
    handoff: bool = False
    sources: list[str] = Field(default_factory=list)

    @field_validator("steps")
    @classmethod
    def _nonempty(cls, v: list[str]) -> list[str]:
        v = [s.strip() for s in v if s and s.strip()]
        if not v:
            raise ValueError("steps empty")
        return v
