# resume-cli

AI 驱动的简历解析与 JD 匹配评分命令行工具。

读取 PDF 简历 → 调用大模型提取结构化信息 → 与岗位描述匹配评分，全程一条命令。

---

## 技术选型

| 组件 | 选型 | 原因 |
|------|------|------|
| 语言 | Python 3.11+ | 类型系统完善，AI 生态丰富 |
| CLI 框架 | click | 声明式参数、自动 --help |
| PDF 解析 | pdfplumber | 文字提取准确，API 简洁 |
| AI 调用 | openai SDK | 兼容 OpenAI 协议，支持 DeepSeek 等模型 |
| 数据校验 | pydantic v2 | JSON → 强类型模型，字段校验 |
| 日志 | loguru | 结构化彩色日志，一行配置 |
| Lint/Format | ruff | 兼具 lint 和 format，速度快 |
| 类型检查 | mypy strict | 严格模式，覆盖全部模块 |

---

## 项目结构

```
resume-cli/
├── resume_cli/
│   ├── __init__.py
│   ├── cli.py          # 三个 CLI 命令：parse / extract / score
│   ├── pdf.py          # PDF 文字提取
│   ├── ai.py           # AI 调用、JSON 修复、schema 校验
│   ├── models.py       # Pydantic 数据模型
│   ├── config.py       # 环境变量配置单例
│   └── exceptions.py   # 异常层次结构
├── tests/
│   ├── fixtures/       # 测试用 PDF 和 JD 文件
│   ├── test_pdf.py
│   ├── test_ai.py
│   └── test_cli.py
├── docs/               # 分步开发记录
├── .env                # 本地环境变量（不提交）
├── .env.example        # 环境变量模板
├── pyproject.toml      # 项目配置 + 所有工具配置
├── Makefile            # 常用命令快捷方式
└── Dockerfile          # 容器化运行
```

---

## 安装

**本地开发**

```bash
python -m venv venv && source venv/bin/activate
make install-dev   # 安装依赖 + pre-commit hooks
```

**仅安装运行时**

```bash
pip install -e .
```

---

## 配置

复制模板并填写 API Key：

```bash
cp .env.example .env
```

`.env` 内容示例：

```env
# OpenAI 官方
OPENAI_API_KEY=sk-xxx

# 或使用 DeepSeek（推荐，兼容 OpenAI 协议）
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
```

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | API Key（必填） | — |
| `OPENAI_BASE_URL` | 自定义 API 地址，不填则走 OpenAI 官方 | — |
| `OPENAI_MODEL` | 模型名称 | `gpt-4o-mini` |
| `AI_TIMEOUT` | 请求超时秒数 | `30` |
| `LOG_LEVEL` | 日志级别 | `INFO` |

---

## CLI 命令

### `parse` — 提取 PDF 原文

```
resume-cli parse <pdf_path> [-o output] [-v]
```

读取 PDF，返回原始文字和字符数，不调用 AI。

```bash
resume-cli parse resume.pdf
```

```json
{
  "char_count": 3687,
  "text": "张三 - 前端开发工程师\n男/1998.10 ..."
}
```

---

### `extract` — AI 结构化提取

```
resume-cli extract <pdf_path> [--mock] [-o output] [-v]
```

调用 AI 从简历中提取姓名、联系方式、教育经历、技能列表。

```bash
resume-cli extract resume.pdf
```

```json
{
  "name": "张三",
  "phone": "15235803633",
  "email": "li1348313766@163.com",
  "city": "",
  "education": [
    {
      "school": "沈阳工业大学",
      "major": "计算机科学与技术",
      "degree": "本科",
      "graduation_time": "2020.6"
    }
  ],
  "skills": [
    "React", "Vue", "Taro", "UniApp", "Webpack", "Vite",
    "LangChain", "LangGraph", "Node.js", "TypeScript", "Next.js"
  ]
}
```

---

### `score` — JD 匹配评分

```
resume-cli score <pdf_path> --jd <jd_path> [--mock] [-o output] [-v]
```

对比简历与岗位描述，输出多维度评分和建议面试问题。

```bash
resume-cli score resume.pdf --jd jd.txt
```

```json
{
  "overall_score": 75,
  "skill_score": 80,
  "experience_score": 70,
  "education_score": 100,
  "comment": "候选人具备扎实的前端技能（React、Node.js）和全栈开发经验，学历符合要求。但后端语言仅提及 Node.js，未明确使用 Python 或 Golang；缺乏专有云项目经验。整体匹配度良好，关键技能有差距。",
  "interview_questions": [
    "请详细描述你使用 Python 或 Golang 进行后端开发的具体项目经验。",
    "你是否有专有云（如阿里云专有云、华为云 Stack）相关的项目经验？",
    "在易网向数字科技公司的短期任职中，你的主要工作内容和离职原因是什么？"
  ]
}
```

---

### 通用选项

| 选项 | 说明 |
|------|------|
| `--mock` | 返回固定 mock 数据，无需 API Key，适合演示 |
| `-o / --output <file>` | 将 JSON 结果同时保存到文件 |
| `-v / --verbose` | 输出 debug 日志（模型、耗时、token 数） |
| `--help` | 查看帮助 |

---

## Mock 模式

没有 API Key 时，用 `--mock` 跑完整流程：

```bash
resume-cli extract resume.pdf --mock
resume-cli score resume.pdf --jd jd.txt --mock
```

mock 返回固定样例数据，与实际 PDF / JD 内容无关，仅用于验证 CLI 流程。

---

## Docker

```bash
docker build -t resume-cli .
docker run --rm --env-file .env \
  -v $(pwd)/resume.pdf:/app/resume.pdf \
  -v $(pwd)/jd.txt:/app/jd.txt \
  resume-cli score /app/resume.pdf --jd /app/jd.txt
```

---

## 开发命令

```bash
make lint        # ruff lint 检查
make format      # ruff 自动格式化
make type-check  # mypy 严格类型检查
make test        # 运行全部测试（29 个）
make clean       # 清理缓存文件
```

---

## 已实现功能

- `parse` / `extract` / `score` 三个核心命令
- PDF 文字提取，含 4 类边界错误处理（不存在 / 非 PDF / 无法读取 / 文字为空）
- AI JSON 响应自动修复（markdown fence、散文包裹、trailing comma）
- Pydantic 严格 schema 校验，评分字段自动 clamp 到 0-100
- `--mock` 演示模式、`--output` 文件保存、`--verbose` debug 日志
- 29 个单元测试，覆盖 PDF / AI / CLI 三层，含真实 PDF 集成测试
- mypy strict + ruff + pre-commit hooks + GitHub Actions CI
- Makefile + Dockerfile

---

## 已知问题 / 未完成

- 不支持扫描版 PDF（图片型简历需 OCR，当前版本会提示"PDF 无可提取文字"）
- mock 模式返回固定样例数据，与实际输入内容无关
- 暂不支持批量处理多份简历
