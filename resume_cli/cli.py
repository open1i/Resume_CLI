"""CLI entry point — three commands: parse, extract, score."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from loguru import logger

from resume_cli import __version__
from resume_cli.ai import extract_resume, score_resume
from resume_cli.exceptions import AIError, JDError, PDFError, ValidationError
from resume_cli.pdf import extract_text

__all__ = ["main"]


_LOG_FMT = "<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}"


def _progress(msg: str, pct: int) -> None:
    """Print a progress bar to stderr, overwriting the current line."""
    bar_len = 25
    filled = bar_len * pct // 100
    bar = "█" * filled + "░" * (bar_len - filled)
    click.echo(f"\r[{bar}] {pct:3d}%  {msg}", nl=False, err=True)
    if pct == 100:
        click.echo("", err=True)


def _configure_logging(verbose: bool) -> None:
    logger.remove()
    level = "DEBUG" if verbose else "WARNING"
    logger.add(sys.stderr, level=level, format=_LOG_FMT)


def _write_output(data: dict[str, object], output: str | None) -> None:
    formatted = json.dumps(data, ensure_ascii=False, indent=2)
    click.echo(formatted)
    if output:
        Path(output).write_text(formatted, encoding="utf-8")
        click.echo(f"Saved to {output}", err=True)


def _read_jd(jd_path: str) -> str:
    path = Path(jd_path)
    if not path.exists():
        raise JDError(f"JD file not found: {jd_path}")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise JDError(f"JD file is empty: {jd_path}")
    return text


def _abort(msg: str) -> None:
    click.secho(f"Error: {msg}", fg="red", err=True)
    sys.exit(1)


@click.group()
@click.version_option(__version__, prog_name="resume-cli")
def main() -> None:
    """AI-powered resume parsing and scoring CLI."""


@main.command()
@click.argument("pdf_path")
@click.option("--output", "-o", default=None, help="Save result to file")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
def parse(pdf_path: str, output: str | None, verbose: bool) -> None:
    """Extract raw text from a PDF resume."""
    _configure_logging(verbose)
    _progress("Reading PDF...", 0)
    try:
        text = extract_text(pdf_path)
    except PDFError as e:
        click.echo("", err=True)
        _abort(str(e))
        return

    _progress("Done", 100)
    result = {"char_count": len(text), "text": text}
    _write_output(result, output)


@main.command()
@click.argument("pdf_path")
@click.option("--output", "-o", default=None, help="Save result to file")
@click.option("--mock", is_flag=True, help="Return mock result (no API key needed)")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
def extract(pdf_path: str, output: str | None, mock: bool, verbose: bool) -> None:
    """Extract structured info from a PDF resume using AI."""
    _configure_logging(verbose)
    try:
        _progress("Reading PDF...", 0)
        text = extract_text(pdf_path)
        _progress("Calling AI...", 50)
        info = extract_resume(text, mock=mock)
    except (PDFError, AIError, ValidationError) as e:
        click.echo("", err=True)
        _abort(str(e))
        return

    _progress("Done", 100)
    _write_output(info.model_dump(), output)


@main.command()
@click.argument("pdf_path")
@click.option("--jd", required=True, help="Path to job description file")
@click.option("--output", "-o", default=None, help="Save result to file")
@click.option("--mock", is_flag=True, help="Return mock result (no API key needed)")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
def score(pdf_path: str, jd: str, output: str | None, mock: bool, verbose: bool) -> None:
    """Score a resume against a job description using AI."""
    _configure_logging(verbose)
    try:
        _progress("Reading JD...", 0)
        jd_text = _read_jd(jd)
        _progress("Reading PDF...", 33)
        resume_text = extract_text(pdf_path)
        _progress("Scoring with AI...", 66)
        result = score_resume(resume_text, jd_text, mock=mock)
    except (PDFError, JDError, AIError, ValidationError) as e:
        click.echo("", err=True)
        _abort(str(e))
        return

    _progress("Done", 100)
    _write_output(result.model_dump(), output)
