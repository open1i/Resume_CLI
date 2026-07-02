"""AI API integration: structured resume extraction and JD scoring."""

from __future__ import annotations

import json
import re
import time
from typing import Any, TypeVar

from loguru import logger
from openai import OpenAI

from resume_cli.config import config
from resume_cli.exceptions import AIError, ValidationError
from resume_cli.models import ResumeInfo, ScoreResult

__all__ = ["extract_resume", "score_resume"]

_T = TypeVar("_T", ResumeInfo, ScoreResult)

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
# Score prompt and mock
# ---------------------------------------------------------------------------

_SCORE_SYSTEM = "你是一位资深 HR 招聘官。只返回合法的 JSON，不要输出任何 markdown 或解释文字。"

_SCORE_USER = """\
请根据以下岗位描述，评估候选人简历与岗位的匹配程度。
按照以下 JSON 格式返回评分结果（分数范围 0-100）：

{{
  "overall_score": 综合评分,
  "skill_score": 技能匹配评分,
  "experience_score": 经验匹配评分,
  "education_score": 学历匹配评分,
  "comment": "简要评价候选人与岗位的匹配情况",
  "interview_questions": ["建议面试问题1", "建议面试问题2"]
}}

岗位描述：
{jd}

候选人简历：
{resume}
"""

_MOCK_SCORE: dict[str, Any] = {
    "overall_score": 82,
    "skill_score": 88,
    "experience_score": 80,
    "education_score": 75,
    "comment": "候选人具备较好的全栈开发基础，技能与岗位要求较匹配，但缺少明确的大模型应用经验。",
    "interview_questions": [
        "请介绍一个你主导过的全栈项目，重点说明你的技术选型理由。",
        "你是否有调用大模型 API 的实际经验？遇到过哪些坑？",
    ],
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


def _parse_response(raw: str, model_cls: type[_T]) -> _T:
    """Repair, parse, and validate an AI JSON response."""
    repaired = _repair_json(raw)
    try:
        data = json.loads(repaired)
    except json.JSONDecodeError as exc:
        logger.debug("Raw AI response:\n{}", raw)
        raise ValidationError(f"AI returned invalid JSON: {exc}") from exc

    try:
        return model_cls(**data)
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
    return _parse_response(raw, ResumeInfo)


def score_resume(resume_text: str, jd_text: str, *, mock: bool = False) -> ScoreResult:
    """Return AI-generated match score between resume and job description."""
    if mock:
        logger.info("Mock mode — returning sample score result")
        return ScoreResult(**_MOCK_SCORE)

    raw = _call_ai(_SCORE_SYSTEM, _SCORE_USER.format(jd=jd_text, resume=resume_text))
    return _parse_response(raw, ScoreResult)
