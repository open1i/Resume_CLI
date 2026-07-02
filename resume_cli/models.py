"""Pydantic models for structured resume data and scoring results."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

__all__ = ["Education", "ResumeInfo", "ScoreResult"]


class Education(BaseModel):
    school: str = ""
    major: str = ""
    degree: str = ""
    graduation_time: str = ""


class ResumeInfo(BaseModel):
    name: str = ""
    phone: str = ""
    email: str = ""
    city: str = ""
    education: list[Education] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)


class ScoreResult(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    skill_score: int = Field(ge=0, le=100)
    experience_score: int = Field(ge=0, le=100)
    education_score: int = Field(ge=0, le=100)
    comment: str = ""
    interview_questions: list[str] = Field(default_factory=list)

    @field_validator(
        "overall_score",
        "skill_score",
        "experience_score",
        "education_score",
        mode="before",
    )
    @classmethod
    def clamp_score(cls, v: Any) -> int:
        return max(0, min(100, int(v)))
