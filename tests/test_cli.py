"""Unit tests for CLI commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from resume_cli.cli import main
from resume_cli.exceptions import AIError, PDFError
from resume_cli.models import Education, ResumeInfo, ScoreResult


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_resume_info() -> ResumeInfo:
    return ResumeInfo(
        name="张三",
        phone="138-0000-0000",
        email="zhangsan@example.com",
        city="杭州",
        education=[Education(school="浙大", major="CS", degree="本科", graduation_time="2022")],
        skills=["Python", "React"],
    )


def _make_score_result() -> ScoreResult:
    return ScoreResult(
        overall_score=82,
        skill_score=88,
        experience_score=80,
        education_score=75,
        comment="匹配度较高",
        interview_questions=["请介绍全栈项目经验"],
    )


# ---------------------------------------------------------------------------
# parse
# ---------------------------------------------------------------------------


def test_parse_file_not_found() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["parse", "/nonexistent.pdf"])
    # 文件不存在应退出码非 0，错误信息写到 stderr
    assert result.exit_code != 0


def test_parse_success() -> None:
    runner = CliRunner()
    with patch("resume_cli.cli.extract_text", return_value="张三\nPython 工程师"):
        result = runner.invoke(main, ["parse", "resume.pdf"])
    assert result.exit_code == 0
    assert "张三" in result.output
    assert "char_count" in result.output


def test_parse_output_flag(tmp_path: Path) -> None:
    out = tmp_path / "out.json"
    runner = CliRunner()
    with patch("resume_cli.cli.extract_text", return_value="简历文本"):
        result = runner.invoke(main, ["parse", "resume.pdf", "-o", str(out)])
    assert result.exit_code == 0
    # --output 应将结果写入文件
    assert out.exists()
    assert "简历文本" in out.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# extract
# ---------------------------------------------------------------------------


def test_extract_mock() -> None:
    runner = CliRunner()
    with patch("resume_cli.cli.extract_text", return_value="任意文本"):
        result = runner.invoke(main, ["extract", "resume.pdf", "--mock"])
    assert result.exit_code == 0
    assert "张三" in result.output
    assert "skills" in result.output


def test_extract_pdf_error() -> None:
    runner = CliRunner()
    with patch("resume_cli.cli.extract_text", side_effect=PDFError("File not found: x.pdf")):
        result = runner.invoke(main, ["extract", "x.pdf", "--mock"])
    assert result.exit_code != 0


def test_extract_ai_error() -> None:
    runner = CliRunner()
    with patch("resume_cli.cli.extract_text", return_value="文本"), \
         patch("resume_cli.cli.extract_resume", side_effect=AIError("API key missing")):
        result = runner.invoke(main, ["extract", "resume.pdf"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# score
# ---------------------------------------------------------------------------


def test_score_mock(tmp_path: Path) -> None:
    jd_file = tmp_path / "jd.txt"
    jd_file.write_text("全栈工程师岗位要求")
    runner = CliRunner()
    with patch("resume_cli.cli.extract_text", return_value="简历文本"):
        result = runner.invoke(main, ["score", "resume.pdf", "--jd", str(jd_file), "--mock"])
    assert result.exit_code == 0
    assert "overall_score" in result.output
    assert "interview_questions" in result.output


def test_score_jd_not_found() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["score", "resume.pdf", "--jd", "/nonexistent/jd.txt"])
    assert result.exit_code != 0


def test_score_jd_empty(tmp_path: Path) -> None:
    jd_file = tmp_path / "empty.txt"
    jd_file.write_text("   ")
    runner = CliRunner()
    result = runner.invoke(main, ["score", "resume.pdf", "--jd", str(jd_file)])
    assert result.exit_code != 0


def test_score_output_flag(tmp_path: Path) -> None:
    jd_file = tmp_path / "jd.txt"
    jd_file.write_text("岗位描述")
    out = tmp_path / "result.json"
    runner = CliRunner()
    with patch("resume_cli.cli.extract_text", return_value="简历文本"):
        result = runner.invoke(
            main, ["score", "resume.pdf", "--jd", str(jd_file), "--mock", "-o", str(out)]
        )
    assert result.exit_code == 0
    assert out.exists()
    assert "overall_score" in out.read_text(encoding="utf-8")
