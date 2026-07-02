"""AI API integration: structured resume extraction."""

from __future__ import annotations

import json
import re
import time
from typing import Any

from loguru import logger
from openai import OpenAI

from resume_cli.config import config
from resume_cli.exceptions import AIError, ValidationError
from resume_cli.models import ResumeInfo

__all__ = ["extract_resume"]

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_EXTRACT_SYSTEM = "你是一个简历解析助手。只返回合法的 JSON，不要输出任何 markdown 或解释文字。"

_EXTRACT_USER = """\
从下面的简历文本中提取结构化信息。
按照以下 JSON 格式返回（缺失字段用空字符串或空数组）：

{{
  "name": "姓名",
  "phone": "电话",
  "email": "邮箱",
  "city": "所在城市",
  "education": [
    {{
      "school": "学校名称",
      "major": "专业",
      "degree": "学历（如本科、硕士、博士）",
      "graduation_time": "毕业时间"
    }}
  ],
  "skills": ["技能1", "技能2"]
}}

简历内容：
{text}
"""

# ---------------------------------------------------------------------------
# Mock response (demo without API key)
# ---------------------------------------------------------------------------

_MOCK_EXTRACT: dict[str, Any] = {
    "name": "张三",
    "phone": "138-0000-0000",
    "email": "zhangsan@example.com",
    "city": "杭州",
    "education": [
        {
            "school": "浙江大学",
            "major": "计算机科学",
            "degree": "本科",
            "graduation_time": "2022-06",
        }
    ],
    "skills": ["Python", "React", "PostgreSQL", "Docker", "FastAPI"],
}

# ---------------------------------------------------------------------------
# JSON repair
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)
_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)
_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")


def _repair_json(raw: str) -> str:
    """Strip markdown fences and fix common JSON formatting issues."""
    cleaned = _FENCE_RE.sub("", raw).strip()

    # Extract first JSON object if the model wrapped it in prose
    match = _OBJECT_RE.search(cleaned)
    if match:
        cleaned = match.group(0)

    # Remove trailing commas before } or ]
    cleaned = _TRAILING_COMMA_RE.sub(r"\1", cleaned)

    return cleaned.strip()


# ---------------------------------------------------------------------------
# Low-level API call
# ---------------------------------------------------------------------------


def _call_ai(system: str, user: str) -> str:
    """Send a chat completion request and return the raw text content."""
    if not config.api_key:
        raise AIError(
            "OPENAI_API_KEY is not set. "
            "Copy .env.example → .env and fill in your key, or pass --mock for demo."
        )

    client = OpenAI(
        api_key=config.api_key,
        base_url=config.base_url,
        timeout=config.timeout,
    )

    logger.debug("Calling model '{}' …", config.model)
    t0 = time.monotonic()

    try:
        response = client.chat.completions.create(
            model=config.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0,
        )
    except Exception as exc:
        raise AIError(f"AI API call failed: {exc}") from exc

    elapsed = time.monotonic() - t0
    usage = response.usage
    logger.debug(
        "Done in {:.2f}s — {} prompt + {} completion tokens",
        elapsed,
        usage.prompt_tokens if usage else "?",
        usage.completion_tokens if usage else "?",
    )

    return response.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Parse + validate AI response
# ---------------------------------------------------------------------------


def _parse_response(raw: str) -> ResumeInfo:
    """Repair, parse, and validate an AI JSON response."""
    repaired = _repair_json(raw)
    try:
        data = json.loads(repaired)
    except json.JSONDecodeError as exc:
        logger.debug("Raw AI response:\n{}", raw)
        raise ValidationError(f"AI returned invalid JSON: {exc}") from exc

    try:
        return ResumeInfo(**data)
    except Exception as exc:
        raise ValidationError(f"AI response failed schema validation: {exc}") from exc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_resume(text: str, *, mock: bool = False) -> ResumeInfo:
    """Return structured resume information extracted by AI."""
    if mock:
        logger.info("Mock mode — returning sample extract result")
        return ResumeInfo(**_MOCK_EXTRACT)

    raw = _call_ai(_EXTRACT_SYSTEM, _EXTRACT_USER.format(text=text))
    return _parse_response(raw)
