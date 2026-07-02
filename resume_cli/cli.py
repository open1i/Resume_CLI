"""CLI entry point — three commands: parse, extract, score."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import click
from loguru import logger

from resume_cli import __version__
from resume_cli.ai import extract_resume, score_resume
from resume_cli.exceptions import AIError, JDError, PDFError, ValidationError
from resume_cli.pdf import extract_text

__all__ = ["main"]


def _configure_logging(verbose: bool) -> None:
    logger.remove()
    level = "DEBUG" if verbose else "WARNING"
    logger.add(sys.stderr, level=level, format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}")


def _write_output(data: dict[str, object], output: Optional[str]) -> None:
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
def parse(pdf_path: str, output: Optional[str], verbose: bool) -> None:
    """Extract raw text from a PDF resume."""
    _configure_logging(verbose)
    try:
        text = extract_text(pdf_path)
    except PDFError as e:
        _abort(str(e))
        return

    result = {"char_count": len(text), "text": text}
    _write_output(result, output)


@main.command()
@click.argument("pdf_path")
@click.option("--output", "-o", default=None, help="Save result to file")
@click.option("--mock", is_flag=True, help="Return mock result (no API key needed)")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
def extract(pdf_path: str, output: Optional[str], mock: bool, verbose: bool) -> None:
    """Extract structured info from a PDF resume using AI."""
    _configure_logging(verbose)
    try:
        text = extract_text(pdf_path)
        info = extract_resume(text, mock=mock)
    except (PDFError, AIError, ValidationError) as e:
        _abort(str(e))
        return

    _write_output(info.model_dump(), output)


@main.command()
@click.argument("pdf_path")
@click.option("--jd", required=True, help="Path to job description file")
@click.option("--output", "-o", default=None, help="Save result to file")
@click.option("--mock", is_flag=True, help="Return mock result (no API key needed)")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
def score(pdf_path: str, jd: str, output: Optional[str], mock: bool, verbose: bool) -> None:
    """Score a resume against a job description using AI."""
    _configure_logging(verbose)
    try:
        jd_text = _read_jd(jd)
        resume_text = extract_text(pdf_path)
        result = score_resume(resume_text, jd_text, mock=mock)
    except (PDFError, JDError, AIError, ValidationError) as e:
        _abort(str(e))
        return

    _write_output(result.model_dump(), output)
