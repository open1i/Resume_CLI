"""PDF text extraction with explicit error boundaries."""

from __future__ import annotations

from pathlib import Path

import pdfplumber
from loguru import logger

from resume_cli.exceptions import PDFError

__all__ = ["extract_text"]


def extract_text(pdf_path: str) -> str:
    """Extract plain text from a local PDF file.

    Raises:
        PDFError: file not found / wrong extension / unreadable / empty text.
    """
    path = Path(pdf_path)

    if not path.exists():
        raise PDFError(f"File not found: {pdf_path}")

    if path.suffix.lower() != ".pdf":
        raise PDFError(f"Not a PDF file: {pdf_path} (got '{path.suffix}')")

    logger.debug("Opening PDF: {}", pdf_path)

    try:
        with pdfplumber.open(str(path)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
    except PDFError:
        raise
    except Exception as exc:
        raise PDFError(f"Cannot read PDF: {exc}") from exc

    text = "\n".join(pages).strip()

    if not text:
        raise PDFError(
            "PDF contains no extractable text — it may be scanned or image-based"
        )

    logger.debug("Extracted {} chars from {} page(s)", len(text), len(pages))
    return text
