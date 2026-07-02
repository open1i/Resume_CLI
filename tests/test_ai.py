"""Unit tests for AI integration module."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from resume_cli.ai import _repair_json, extract_resume, score_resume
from resume_cli.exceptions import AIError, ValidationError
from resume_cli.models import ResumeInfo, ScoreResult

# ---------------------------------------------------------------------------
# _repair_json
# ---------------------------------------------------------------------------


def test_repair_strips_markdown_fence() -> None:
    raw = '```json\n{"name": "张三"}\n```'
    assert _repair_json(raw) == '{"name": "张三"}'


def test_repair_strips_prose_around_json() -> None:
    raw = 'Here is the result:\n{"name": "张三"}\nDone.'
    assert _repair_json(raw) == '{"name": "张三"}'


def test_repair_removes_trailing_comma() -> None:
    raw = '{"name": "张三", "skills": ["Python",]}'
    result = _repair_json(raw)
    assert result == '{"name": "张三", "skills": ["Python"]}'


# ---------------------------------------------------------------------------
# mock mode
# ---------------------------------------------------------------------------


def test_extract_mock_returns_resume_info() -> None:
    result = extract_resume("any text", mock=True)
    assert isinstance(result, ResumeInfo)
    assert result.name == "张三"
    assert "Python" in result.skills


# ---------------------------------------------------------------------------
# missing API key
# ---------------------------------------------------------------------------


def test_extract_raises_when_no_api_key() -> None:
    with patch("resume_cli.ai.config") as mock_config:
        mock_config.api_key = ""
        with pytest.raises(AIError, match="OPENAI_API_KEY"):
            extract_resume("some text")


# ---------------------------------------------------------------------------
# API call failure
# ---------------------------------------------------------------------------


def test_extract_raises_on_api_error() -> None:
    # 同时 mock config 和 OpenAI 客户端：config 提供合法 key 让代码通过前置检查，
    # 再让 create() 抛异常，验证网络/接口层错误被正确包装成 AIError
    with patch("resume_cli.ai.config") as mock_config:
        mock_config.api_key = "sk-test"
        mock_config.base_url = None
        mock_config.timeout = 30
        mock_config.model = "gpt-4o-mini"
        with patch("resume_cli.ai.OpenAI") as mock_openai:
            mock_openai.return_value.chat.completions.create.side_effect = Exception(
                "connection error"
            )
            with pytest.raises(AIError, match="AI API call failed"):
                extract_resume("some text")


# ---------------------------------------------------------------------------
# invalid JSON response
# ---------------------------------------------------------------------------


def test_extract_raises_on_invalid_json() -> None:
    # 直接 mock _call_ai 跳过真实 API 调用，专注测试 JSON 解析这一层的错误处理
    with (
        patch("resume_cli.ai._call_ai", return_value="not json at all %%%"),
        pytest.raises(ValidationError, match="invalid JSON"),
    ):
        extract_resume("some text")


def test_extract_raises_on_schema_mismatch() -> None:
    # education 字段期望 list，传入 string 会让 Pydantic 抛类型错误
    # 外层 patch 会被内层覆盖，内层才是真正生效的 mock
    with (
        patch("resume_cli.ai._call_ai", return_value='{"unexpected_field": 999}'),
        patch("resume_cli.ai._call_ai", return_value='{"education": "not a list"}'),
        pytest.raises(ValidationError, match="schema validation"),
    ):
        extract_resume("some text")


# ---------------------------------------------------------------------------
# score_resume
# ---------------------------------------------------------------------------


def test_score_mock_returns_score_result() -> None:
    result = score_resume("简历内容", "岗位描述", mock=True)
    assert isinstance(result, ScoreResult)
    assert 0 <= result.overall_score <= 100
    assert len(result.interview_questions) >= 1


def test_score_mock_clamps_score_over_100() -> None:
    # 验证即使 mock 数据分数超出范围，Pydantic 的 clamp_score validator 也能修正
    with patch(
        "resume_cli.ai._MOCK_SCORE",
        {
            **{
                "overall_score": 150,
                "skill_score": 88,
                "experience_score": 80,
                "education_score": 75,
                "comment": "test",
                "interview_questions": [],
            }
        },
    ):
        result = score_resume("简历", "JD", mock=True)
        assert result.overall_score == 100


def test_score_raises_on_schema_mismatch() -> None:
    # interview_questions 期望 list，传入 string 触发 Pydantic 校验失败
    with (
        patch("resume_cli.ai._call_ai", return_value='{"interview_questions": "not a list"}'),
        pytest.raises(ValidationError, match="schema validation"),
    ):
        score_resume("简历", "JD")
