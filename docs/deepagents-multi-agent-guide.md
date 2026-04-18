# 基于 DeepAgents 的论文复现多智能体开发指南

## 概述

本文档给出一套更贴合 `MultiAgentPaperCoder` 的 `deepagents` 版多智能体实现方案。目标不是泛泛介绍框架，而是围绕当前项目的核心任务来设计：

- 输入一篇论文 PDF
- 提取论文关键信息
- 生成复现代码
- 执行基础验证
- 在失败时给出修复建议并继续迭代

这套方案适合你当前项目的原因很直接：

- 你现在的项目已经是典型的多阶段论文复现流程
- 现有职责已经天然分成 4 个角色
- `deepagents` 可以把“规划、子智能体、文件上下文、记忆、人审”这些通用能力直接接管
- 你只需要把项目特定的工具层和约束补上

官方资料：

- LangGraph: <https://docs.langchain.com/oss/python/langgraph/overview>
- Deep Agents: <https://docs.langchain.com/oss/python/deepagents/overview>
- Deep Agents Customization: <https://docs.langchain.com/oss/python/deepagents/customization>
- Deep Agents Subagents: <https://docs.langchain.com/oss/python/deepagents/subagents>

## 这份指南解决什么问题

当前仓库的 LangGraph 版本更偏“显式状态机”：

- `DocumentAnalysisAgent`
- `CodeGenerationAgent`
- `CodeVerificationAgent`
- `ErrorRepairAgent`

如果改成 `deepagents` 版，不再把所有流程都写死在图里，而是改成：

- 一个主智能体负责规划和调度
- 四个子智能体负责专业工作
- 一组工具负责 PDF 读取、文件写入、代码检查
- 用 `deepagents` 自带的 todo、subagent、filesystem、memory、interrupt 能力做通用编排

这意味着：

- 好处：开发更快，提示词和工具更容易演化
- 代价：流程控制不如纯 LangGraph 那么硬

所以最务实的建议是：

- 外层用 `deepagents`
- 高风险执行步骤继续保留确定性工具
- 将来如果验证和修复需要严格循环，再把那一段下沉成 LangGraph 子流程

## 面向当前项目的角色拆分

建议保留你现在的四角色，只是换成 `deepagents` 的子智能体定义方式。

### 主智能体

职责：

- 接收用户请求
- 规划任务步骤
- 决定调用哪个子智能体
- 汇总最终结果

### 文档分析子智能体

职责：

- 读取 PDF
- 提取论文标题、问题定义、方法核心逻辑
- 提取需要实现的模块
- 输出代码生成所需的结构化分析结果

### 代码生成子智能体

职责：

- 根据论文分析结果生成项目骨架
- 生成 `main.py`、模型文件、数据处理文件等
- 生成 `requirements.txt`

### 代码验证子智能体

职责：

- 检查生成代码的文件结构
- 做 Python 语法检查
- 做最小可运行性验证
- 汇总错误

### 错误修复子智能体

职责：

- 根据错误日志定位根因
- 给出修复方案
- 重写相关文件
- 交回验证子智能体继续检查

## 推荐目录结构

下面这套结构是“最小但完整、可以跑起来”的版本。

```text
papercoder_deepagents/
├── .env.example
├── requirements.txt
├── README.md
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── agent.py
│   ├── config.py
│   ├── schemas.py
│   ├── prompts.py
│   ├── subagents.py
│   └── tools/
│       ├── __init__.py
│       ├── pdf_tools.py
│       ├── artifact_tools.py
│       └── exec_tools.py
├── output/
│   ├── artifacts/
│   └── generated_code/
└── paper_examples/
```

## 运行逻辑

主智能体的理想工作流是：

1. 读取用户输入和 PDF 路径
2. 调用文档分析子智能体
3. 调用代码生成子智能体
4. 调用代码验证子智能体
5. 如果失败，调用错误修复子智能体
6. 再次调用代码验证子智能体
7. 输出总结报告

这里和 LangGraph 版最大的区别是：

- LangGraph 版是显式边和条件路由
- `deepagents` 版是主智能体依据系统提示和工具结果自行调度

因此系统提示必须写得足够明确。

## 依赖

`requirements.txt`

```txt
deepagents
langchain-openai
python-dotenv
pydantic>=2
pypdf
```

如果你想换 Anthropic，把 `langchain-openai` 换成 `langchain-anthropic` 即可。

## 环境变量

`.env.example`

```bash
OPENAI_API_KEY=your_api_key_here
MODEL_NAME=openai:gpt-5.4
OUTPUT_ROOT=./output
```

## 完整可运行代码骨架

下面这套代码是“最小可运行版”。它不是高质量论文复现器，但它具备完整的工程骨架，可以直接作为 `deepagents` 迁移起点。

### 1. `app/config.py`

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    model_name: str = os.getenv("MODEL_NAME", "openai:gpt-5.4")
    output_root: Path = Path(os.getenv("OUTPUT_ROOT", "./output"))

    @property
    def artifacts_dir(self) -> Path:
        return self.output_root / "artifacts"

    @property
    def generated_code_dir(self) -> Path:
        return self.output_root / "generated_code"

    def ensure_dirs(self) -> None:
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.generated_code_dir.mkdir(parents=True, exist_ok=True)
```

### 2. `app/schemas.py`

```python
from __future__ import annotations

from pydantic import BaseModel, Field


class PaperAnalysis(BaseModel):
    title: str = Field(description="论文标题")
    problem: str = Field(description="论文解决的问题")
    method_summary: str = Field(description="方法总体描述")
    modules_to_implement: list[str] = Field(description="需要实现的核心模块")
    training_flow: list[str] = Field(description="训练流程")
    evaluation_flow: list[str] = Field(description="评估流程")
    dependencies: list[str] = Field(description="推测的 Python 依赖")
    risks: list[str] = Field(description="复现风险点")


class VerificationReport(BaseModel):
    success: bool = Field(description="验证是否通过")
    checked_files: list[str] = Field(description="检查过的文件")
    errors: list[str] = Field(description="错误列表")
    summary: str = Field(description="验证摘要")


class RepairPlan(BaseModel):
    root_cause: str = Field(description="根因分析")
    files_to_modify: list[str] = Field(description="需要修改的文件")
    repair_strategy: str = Field(description="修复策略")
```

### 3. `app/prompts.py`

```python
MAIN_SYSTEM_PROMPT = """
你是论文复现项目的主调度智能体。

你的任务是：
1. 先规划，再执行
2. 优先调用合适的子智能体，而不是自己臆造细节
3. 按如下顺序组织工作：
   - 先分析论文
   - 再生成代码
   - 再验证代码
   - 如果失败，再调用修复子智能体，再次验证
4. 所有结论必须基于工具输出或子智能体输出
5. 最终给出：
   - 论文摘要
   - 已生成文件
   - 验证结果
   - 未解决问题
"""


DOCUMENT_ANALYST_PROMPT = """
你是文档分析子智能体。

目标：
- 从 PDF 文本中提取论文的核心方法
- 明确要复现的模块
- 明确训练和评估流程
- 输出必须结构化，避免空泛总结

要求：
- 不要编造论文中不存在的实验设置
- 对不确定内容明确标注
"""


CODE_GENERATOR_PROMPT = """
你是代码生成子智能体。

目标：
- 根据论文分析结果生成最小可运行项目
- 优先生成清晰的 Python 项目结构
- 避免一次性写出过度复杂的工程

要求：
- 至少生成 main.py 和 requirements.txt
- 如果无法完整实现，先生成合理骨架和 TODO 注释
"""


VERIFIER_PROMPT = """
你是代码验证子智能体。

目标：
- 基于工具检查输出目录中的 Python 代码
- 首先做语法检查
- 然后检查入口文件是否存在
- 最后输出结构化验证报告
"""


REPAIR_PROMPT = """
你是错误修复子智能体。

目标：
- 根据验证阶段的错误信息定位问题
- 给出精确修复方案
- 只改必要文件
- 修复后提醒主智能体重新验证
"""
```

### 4. `app/tools/pdf_tools.py`

```python
from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def read_pdf_text(pdf_path: str) -> str:
    """读取 PDF 文本，返回截断后的全文。"""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    reader = PdfReader(str(path))
    chunks: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            chunks.append(text.strip())

    full_text = "\n\n".join(chunks)
    if not full_text:
        raise ValueError("PDF text extraction returned empty content")

    return full_text[:50000]
```

### 5. `app/tools/artifact_tools.py`

```python
from __future__ import annotations

from pathlib import Path


def save_text_file(path: str, content: str) -> str:
    """写文本文件。"""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return f"saved: {file_path}"


def read_text_file(path: str) -> str:
    """读文本文件。"""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return file_path.read_text(encoding="utf-8")


def list_files(root_dir: str) -> str:
    """列出目录下文件。"""
    root = Path(root_dir)
    if not root.exists():
        return ""
    files = [str(p) for p in root.rglob("*") if p.is_file()]
    return "\n".join(sorted(files))
```

### 6. `app/tools/exec_tools.py`

```python
from __future__ import annotations

import py_compile
from pathlib import Path


def python_syntax_check(root_dir: str) -> str:
    """对目录下所有 Python 文件做语法检查。"""
    root = Path(root_dir)
    if not root.exists():
        raise FileNotFoundError(f"Directory not found: {root_dir}")

    checked: list[str] = []
    errors: list[str] = []

    for file_path in root.rglob("*.py"):
        try:
            py_compile.compile(str(file_path), doraise=True)
            checked.append(str(file_path))
        except py_compile.PyCompileError as exc:
            errors.append(f"{file_path}: {exc.msg}")

    if errors:
        return "FAILED\n" + "\n".join(errors)

    return "PASSED\n" + "\n".join(checked)
```

### 7. `app/subagents.py`

```python
from __future__ import annotations

from app.prompts import (
    CODE_GENERATOR_PROMPT,
    DOCUMENT_ANALYST_PROMPT,
    REPAIR_PROMPT,
    VERIFIER_PROMPT,
)
from app.schemas import PaperAnalysis, RepairPlan, VerificationReport
from app.tools.artifact_tools import list_files, read_text_file, save_text_file
from app.tools.exec_tools import python_syntax_check
from app.tools.pdf_tools import read_pdf_text


def build_subagents(artifacts_dir: str, generated_code_dir: str) -> list[dict]:
    return [
        {
            "name": "document-analyst",
            "description": "读取 PDF 并提取论文复现所需的结构化信息",
            "system_prompt": DOCUMENT_ANALYST_PROMPT,
            "tools": [read_pdf_text, save_text_file],
            "response_format": PaperAnalysis,
        },
        {
            "name": "code-generator",
            "description": "根据论文分析结果生成代码骨架和项目文件",
            "system_prompt": CODE_GENERATOR_PROMPT,
            "tools": [save_text_file, read_text_file, list_files],
        },
        {
            "name": "code-verifier",
            "description": "检查生成代码的结构和 Python 语法是否正确",
            "system_prompt": VERIFIER_PROMPT,
            "tools": [list_files, read_text_file, python_syntax_check],
            "response_format": VerificationReport,
        },
        {
            "name": "error-repairer",
            "description": "根据错误日志修复生成代码中的问题",
            "system_prompt": REPAIR_PROMPT,
            "tools": [read_text_file, save_text_file, list_files],
            "response_format": RepairPlan,
        },
    ]
```

### 8. `app/agent.py`

```python
from __future__ import annotations

from deepagents import create_deep_agent

from app.config import Settings
from app.prompts import MAIN_SYSTEM_PROMPT
from app.subagents import build_subagents
from app.tools.artifact_tools import list_files, read_text_file, save_text_file
from app.tools.exec_tools import python_syntax_check
from app.tools.pdf_tools import read_pdf_text


def build_agent(settings: Settings):
    settings.ensure_dirs()

    tools = [
        read_pdf_text,
        save_text_file,
        read_text_file,
        list_files,
        python_syntax_check,
    ]

    subagents = build_subagents(
        artifacts_dir=str(settings.artifacts_dir),
        generated_code_dir=str(settings.generated_code_dir),
    )

    agent = create_deep_agent(
        model=settings.model_name,
        tools=tools,
        system_prompt=MAIN_SYSTEM_PROMPT,
        subagents=subagents,
        interrupt_on={
            "save_text_file": False,
        },
    )
    return agent
```

### 9. `app/main.py`

```python
from __future__ import annotations

import argparse
from pathlib import Path

from app.agent import build_agent
from app.config import Settings


def build_user_prompt(pdf_path: str, output_dir: str) -> str:
    return f"""
请执行一轮论文复现任务，要求如下：

1. 读取论文 PDF：{pdf_path}
2. 先调用 document-analyst 提取结构化论文分析
3. 将论文分析保存到 {output_dir}/artifacts/paper_analysis.md 或等价文件
4. 再调用 code-generator，在 {output_dir}/generated_code 下生成最小可运行 Python 项目
5. 项目至少包含：
   - main.py
   - requirements.txt
6. 然后调用 code-verifier 检查生成结果
7. 如果验证失败，调用 error-repairer 修复，再重新验证一次
8. 最终输出：
   - 论文核心方法摘要
   - 生成文件列表
   - 验证是否通过
   - 失败原因或剩余风险
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True, help="论文 PDF 路径")
    parser.add_argument(
        "--output-dir",
        default="./output",
        help="输出目录，默认 ./output",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    settings = Settings(output_root=Path(args.output_dir))
    agent = build_agent(settings)

    user_prompt = build_user_prompt(str(pdf_path), str(settings.output_root))

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": user_prompt,
                }
            ]
        }
    )

    print(result)


if __name__ == "__main__":
    main()
```

### 10. `app/__init__.py`

```python
```

### 11. `app/tools/__init__.py`

```python
```

## 如何运行

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境变量

```bash
cp .env.example .env
```

然后填入你的 API Key。

### 执行

```bash
python -m app.main --pdf ./paper_examples/1607.01759v3.pdf --output-dir ./output
```

## 这套骨架实际会做什么

只要模型可用，这套骨架就可以完成以下最小闭环：

- 读取 PDF 文本
- 由主智能体调度子智能体
- 让文档分析子智能体提炼论文信息
- 让代码生成子智能体写出项目文件
- 让代码验证子智能体对输出目录做 Python 语法检查
- 如有需要，调用错误修复子智能体修改文件

这已经具备“能跑一轮”的最低条件。

## 贴合当前仓库的迁移映射

你当前项目中的模块和 `deepagents` 版可以一一对应：

| 当前项目 | DeepAgents 版映射 |
|----------|-------------------|
| `DocumentAnalysisAgent` | `document-analyst` 子智能体 |
| `CodeGenerationAgent` | `code-generator` 子智能体 |
| `CodeVerificationAgent` | `code-verifier` 子智能体 |
| `ErrorRepairAgent` | `error-repairer` 子智能体 |
| `PaperCoderWorkflow` | 主智能体 + system prompt 调度逻辑 |
| `PDFParser` | `read_pdf_text` 工具 |
| `CodeExecutor` | `python_syntax_check` 或后续扩展执行工具 |

## 建议的第一轮增强

上面的代码骨架能跑，但不够强。第一轮建议增强如下。

### 1. 把论文分析结果持久化成结构化 JSON

当前骨架主要靠模型理解和文本文件。更稳的做法是：

- 文档分析子智能体输出 Pydantic 结构
- 主智能体把结构写成 JSON
- 后续生成和验证都读 JSON，而不是读自由文本

### 2. 增加项目级文件写入约束

现在 `save_text_file` 可以写任意路径。正式版本应该限制：

- 只能写 `output/artifacts/`
- 或 `output/generated_code/`

避免工具滥写。

### 3. 增加更像样的验证工具

目前只是语法检查。建议继续加：

- `check_entrypoint_exists`
- `install_requirements_in_venv`
- `run_smoke_test`
- `capture_traceback`

### 4. 将修复流程收紧

正式版不建议让修复子智能体无限写文件。建议：

- 只允许修改验证阶段明确点名的文件
- 每次修复后必须重新验证
- 超过最大次数后终止

### 5. 为论文复现场景补专用技能

很适合拆成 skills 的内容包括：

- 机器学习论文阅读 checklist
- 模型复现项目结构模板
- 训练脚本常见参数模板
- 实验报告模板

## 更稳妥的主智能体提示词写法

`deepagents` 版成败很大程度上取决于主智能体提示词。建议把调度规则写死一些。

例如：

```text
遇到论文复现任务时，必须遵循：
1. 不允许跳过论文分析直接生成代码
2. 不允许在没有验证的情况下声称代码可运行
3. 验证失败时，优先调用错误修复子智能体
4. 每轮修复后必须重新验证
5. 最终输出必须包含风险项
```

这会明显减少系统在流程上的发散。

## 适合当前项目的工具设计原则

你的项目不是通用聊天机器人，而是论文复现器。所以工具必须围绕“产出代码项目”设计。

建议遵守：

- 工具返回要具体，不要只返回“成功”
- 大文本要落盘，不要全塞进对话上下文
- 所有写文件工具都要可审计
- 所有执行工具都要有超时和错误输出
- 验证工具尽量确定性，不要靠 LLM 猜

## 什么时候不该继续用 DeepAgents

如果将来你发现以下情况越来越多，就应该把关键路径下沉回 LangGraph：

- 修复流程有明确状态转换
- 验证逻辑非常严格
- 必须做固定次数重试
- 必须插入人工审批节点
- 对运行轨迹可解释性要求很高

最现实的演进方式不是“二选一”，而是：

- 外层：`deepagents`
- 内层关键子流程：`LangGraph`

## 推荐落地方案

结合你这个项目，最推荐的方案不是全量替换，而是分三步。

### 第一步

先把主流程迁到 `deepagents`：

- 主智能体
- 4 个子智能体
- PDF、文件、语法检查工具

目标是先让系统“能完整跑一轮”。

### 第二步

保留验证和修复的确定性：

- 固定验证步骤
- 固定错误收集格式
- 固定最大修复次数

目标是避免完全依赖模型自由发挥。

### 第三步

把验证修复循环下沉成 LangGraph 子流程。

目标是：

- 外层保留 `deepagents` 的易开发性
- 内层保留 LangGraph 的强控制力

## 总结

如果你只是想快速搭一套论文复现多智能体系统，`deepagents` 很适合作为外层编排框架，因为它已经把这些高频能力准备好了：

- 规划
- 子智能体
- 文件上下文
- 记忆
- 审批

对于 `MultiAgentPaperCoder`，最自然的改造方式是：

- 沿用现在的四角色拆分
- 用 `deepagents` 主智能体统一调度
- 把 PDF 解析、文件写入、代码检查做成明确工具
- 把验证和修复逐步收紧到确定性流程

上面给出的代码骨架已经足够作为第一版起点。如果你下一步要继续推进，最值得做的是两件事：

- 把这套骨架真正落到 `src/` 里
- 把语法检查升级成真实执行验证
