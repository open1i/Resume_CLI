"""Unit tests and integration tests for PDF text extraction."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from resume_cli.exceptions import PDFError
from resume_cli.pdf import extract_text

SAMPLE_PDF = Path("tests/fixtures/附件简历-李子威-ai前端开发-5年.pdf")


def test_file_not_found() -> None:
    with pytest.raises(PDFError, match="File not found"):
        extract_text("/nonexistent/path/resume.pdf")


def test_not_a_pdf(tmp_path: Path) -> None:
    f = tmp_path / "resume.txt"
    f.write_text("hello")
    with pytest.raises(PDFError, match="Not a PDF"):
        extract_text(str(f))


def test_unreadable_pdf(tmp_path: Path) -> None:
    f = tmp_path / "broken.pdf"
    f.write_bytes(b"not a real pdf")
    with patch("pdfplumber.open", side_effect=Exception("corrupted")):
        with pytest.raises(PDFError, match="Cannot read PDF"):
            extract_text(str(f))


def test_empty_pdf(tmp_path: Path) -> None:
    f = tmp_path / "empty.pdf"
    f.write_bytes(b"%PDF-1.4")

    mock_page = MagicMock()
    mock_page.extract_text.return_value = None
    mock_pdf = MagicMock()
    mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdf.__exit__ = MagicMock(return_value=False)
    mock_pdf.pages = [mock_page]

    with patch("pdfplumber.open", return_value=mock_pdf):
        with pytest.raises(PDFError, match="no extractable text"):
            extract_text(str(f))


def test_success(tmp_path: Path) -> None:
    f = tmp_path / "resume.pdf"
    f.write_bytes(b"%PDF-1.4")

    mock_page = MagicMock()
    mock_page.extract_text.return_value = "张三\nPython 工程师"
    mock_pdf = MagicMock()
    mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdf.__exit__ = MagicMock(return_value=False)
    mock_pdf.pages = [mock_page]

    with patch("pdfplumber.open", return_value=mock_pdf):
        result = extract_text(str(f))

    assert "张三" in result
    assert "Python 工程师" in result


# ---------------------------------------------------------------------------
# Integration tests — real PDF, real pdfplumber
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not SAMPLE_PDF.exists(), reason="fixture PDF not found")
def test_real_pdf_returns_text() -> None:
    text = extract_text(str(SAMPLE_PDF))
    assert len(text) > 100


@pytest.mark.skipif(not SAMPLE_PDF.exists(), reason="fixture PDF not found")
def test_real_pdf_contains_basic_fields() -> None:
    text = extract_text(str(SAMPLE_PDF))
    assert "李子威" in text
    assert "li1348313766@163.com" in text
    assert "15235803633" in text


@pytest.mark.skipif(not SAMPLE_PDF.exists(), reason="fixture PDF not found")
def test_real_pdf_contains_skills() -> None:
    text = extract_text(str(SAMPLE_PDF))
    assert "React" in text
