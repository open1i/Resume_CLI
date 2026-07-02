"""Unit tests and integration tests for PDF text extraction."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from resume_cli.exceptions import PDFError
from resume_cli.pdf import extract_text

SAMPLE_PDF = Path("tests/fixtures/resume-demo.pdf")


def test_file_not_found() -> None:
    # 传入一个根本不存在的路径，验证第一道检查能正确触发
    with pytest.raises(PDFError, match="File not found"):
        extract_text("/nonexistent/path/resume.pdf")


def test_not_a_pdf(tmp_path: Path) -> None:
    # 文件存在但后缀不是 .pdf，验证扩展名检查先于文件读取
    f = tmp_path / "resume.txt"
    f.write_text("hello")
    with pytest.raises(PDFError, match="Not a PDF"):
        extract_text(str(f))


def test_unreadable_pdf(tmp_path: Path) -> None:
    # 文件存在且后缀正确，但 pdfplumber 解析时抛异常（如文件损坏）
    # mock pdfplumber.open 而非真实损坏文件，避免依赖 pdfplumber 的具体错误格式
    f = tmp_path / "broken.pdf"
    f.write_bytes(b"not a real pdf")
    with (
        patch("pdfplumber.open", side_effect=Exception("corrupted")),
        pytest.raises(PDFError, match="Cannot read PDF"),
    ):
        extract_text(str(f))


def test_empty_pdf(tmp_path: Path) -> None:
    # PDF 可以打开，但所有页面 extract_text() 返回 None（扫描件或纯图片 PDF 的典型情况）
    # mock 整个 pdfplumber context manager，模拟"有页但无文字"的状态
    f = tmp_path / "empty.pdf"
    f.write_bytes(b"%PDF-1.4")

    mock_page = MagicMock()
    mock_page.extract_text.return_value = None
    mock_pdf = MagicMock()
    mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdf.__exit__ = MagicMock(return_value=False)
    mock_pdf.pages = [mock_page]

    with (
        patch("pdfplumber.open", return_value=mock_pdf),
        pytest.raises(PDFError, match="no extractable text"),
    ):
        extract_text(str(f))


def test_success(tmp_path: Path) -> None:
    # 正常路径：mock 返回真实文本，验证多页内容被正确拼接后返回
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


# skipif：fixture PDF 不存在时（如 CI 环境未提交该文件）自动跳过，不影响流水线
@pytest.mark.skipif(not SAMPLE_PDF.exists(), reason="fixture PDF not found")
def test_real_pdf_returns_text() -> None:
    # 最基础的集成验证：pdfplumber 能从这份真实简历中提取出足量文本
    text = extract_text(str(SAMPLE_PDF))
    assert len(text) > 100


@pytest.mark.skipif(not SAMPLE_PDF.exists(), reason="fixture PDF not found")
def test_real_pdf_contains_basic_fields() -> None:
    # 验证姓名、邮箱、电话这三个关键字段在提取结果中可以被找到
    text = extract_text(str(SAMPLE_PDF))
    assert "李子威" in text
    assert "li1348313766@163.com" in text
    assert "15235803633" in text


@pytest.mark.skipif(not SAMPLE_PDF.exists(), reason="fixture PDF not found")
def test_real_pdf_contains_skills() -> None:
    # 验证技能关键词可被提取，确保多栏布局不会导致文字丢失
    text = extract_text(str(SAMPLE_PDF))
    assert "React" in text
