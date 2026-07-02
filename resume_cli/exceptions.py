"""Custom exception hierarchy for resume-cli."""

from __future__ import annotations

__all__ = [
    "ResumeCLIError",
    "PDFError",
    "AIError",
    "ValidationError",
    "JDError",
]


class ResumeCLIError(Exception):
    """Base exception — catch this to handle all resume-cli errors."""


class PDFError(ResumeCLIError):
    """PDF file cannot be found, read, or contains no extractable text."""


class AIError(ResumeCLIError):
    """AI API call failed or returned an unusable response."""


class ValidationError(ResumeCLIError):
    """AI response failed JSON parsing or Pydantic schema validation."""


class JDError(ResumeCLIError):
    """Job description file is missing or empty."""
