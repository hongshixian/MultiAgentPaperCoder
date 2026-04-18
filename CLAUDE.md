# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Running the Application

```bash
# Basic usage - process a PDF paper
python -m src.main --pdf path/to/paper.pdf

# Enable verbose output
python -m src.main --pdf paper.pdf --verbose
```

### Running Tests

```bash
# Run all tests with pytest
pytest test_cases/

# Run specific test categories
pytest test_cases/unit/
pytest test_cases/integration/

# Run specific test file
pytest test_cases/unit/test_basic_imports.py

# Run with verbose output
pytest test_cases/ -v

# Run specific test
pytest test_cases/unit/test_config.py::test_app_config_creation
```

### Development Setup

```bash
# Create conda environment
conda create -n py12pt python=3.12
conda activate py12pt

# Install dependencies
pip install -r requirements.txt

# Configure environment (copy and edit .env.example)
cp .env.example .env
```

## Architecture Overview

MultiAgentPaperCoder is a multi-agent system that automates reproduction of research paper code. The system follows a sequential workflow through specialized agents with an iterative repair mechanism. The implementation is built on LangChain and LangGraph ecosystem.

### System Architecture

The system adopts a layered architecture with Agent/Tool separation:

- **Agent Layer**: Responsible for high-level decision-making, planning, and coordination
- **Tool Layer**: Provides specific basic capabilities (PDF parsing, code execution, etc.)
- **LLM Layer**: Abstracts LLM provider selection with streaming support

```
┌─────────────────────────────────────────────────────────┐
│                     第一层：用户界面层                     │
│  ┌───────────────────────────────────────────────────┐  │
│  │                  用户交互界面                      │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                     第二层：调度层                       │
│  ┌───────────────────────────────────────────────────┐  │
│  │     LangGraph 工作流（状态机、条件路由）          │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                     第三层：Agent 层                    │
│  ┌──────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │ 文档分析智能体   │  │ 代码生成智能体 │  │ 代码验证智能体   │  │
│  └──────────────────┘  └────────────────┘  └──────────────────┘  │
│  ┌──────────────────────────────────────────────┐        │
│  │            错误修复智能体                 │        │
│  └──────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                   第四层：Tool/LLM 层               │
│  ┌──────────────────┐  ┌──────────────────┐        │
│  │   PDF 解析工具    │  │  代码执行工具    │        │
│  └──────────────────┘  └──────────────────┘        │
│  ┌──────────────────┐  ┌──────────────────┐        │
│  │   LLM 客户端     │  │  提示词管理器    │        │
│  └──────────────────┘  └──────────────────┘        │
└─────────────────────────────────────────────────────────┘
```

### Agent Layer

**系统有 4 个核心智能体：**

1.
**文档分析智能体** (`src/agents/document_analysis.py`)
   - **功能**: 读取PDF并分析算法
   - 读取和解析 PDF 文件
   - 提取文本、结构、元数据
   - 分析论文内容以提取算法详情
   - 使用 LLM 理解算法逻辑、超参数、需求
   - 返回结构化的算法分析

2. **代码生成智能体** (`src/agents/code_generation.py`)
   - **功能**: 规划并生成代码
   - 根据算法分析结果设计代码结构
   - 规划文件组织、实现步骤、依赖
   - 生成完整的 Python 代码文件
   - 分析代码依赖并生成 requirements.txt
   - 使用 LLM 进行架构决策和代码生成

3. **代码验证智能体** (`src/agents/code_verification.py`)
   - **功能**: 验证代码执行并评估结果
   - 在隔离的 conda 环境中执行生成的代码
   - 监控执行、捕获错误、提供修复建议
   - 验证执行结果是否符合预期结果
   - 评估生成代码执行的质量
   - 使用 CodeExecutor 和 LLM 工具

4. **错误修复智能体** (`src/agents/error_repair_agent.py`)
   - **功能**: 分析错误并生成修复
   - 分析验证报告中的错误信息和运行日志
   - 定位错误原因，判断错误类型
   - 根据错误类型制定修复方案
   - 修改代码中的 bug
   - 调整不合理的超参数或配置
   - 验证修复效果
   - 记录错误修复过程

### Workflow Orchestration

**PaperCoderWorkflow** (`src/graph/workflow.py`) 使用 LangGraph 编排顺序执行和迭代修复：
- 使用 LangGraph 的 StateGraph 进行状态管理
- 实现条件路由（`should_continue_verification`）
- 创建初始状态，包含 `PaperState` 结构
- 处理重试逻辑，使用迭代计数器（max_iterations，默认：5）
- 生成执行摘要

**Workflow flow:**
```
start → 文档分析 → 代码生成 → 代码验证
                           ↓
代码验证 (需要修复) → 错误修复 → 代码验证 ↗
代码验证 (需要重新生成) → 代码生成 → 代码验证 ↗
```

### State Management

**PaperState** (`src/state/__init__.py`) 是 `TypedDict`，在工作流中传递：

**Input fields:**
- `pdf_path`: PDF 文件路径

**Result fields:**
- `paper_content`: PDF 解析结果
- `algorithm_analysis`: 算法分析结果
- `code_plan`: 代码规划结果
- `generated_code`: 生成代码的元数据
- `validation_result`: 验证结果
- `verification_result`: 验证结果
- `repair_history`: 修复尝试的历史记录

**Control fields:**
- `current_step`: 当前工作流步骤
- `errors`: 累积的错误消息
- `iteration_count`: 修复循环的当前迭代次数
- `max_iterations`: 修复循环的最大迭代次数（默认：5）
- `retry_count`: 当前重试计数
- `max_retries`: 最大重试次数（默认：3）

### Tool Layer

1. **LLMClient** (`src/llms/llm_client.py`)
   - 实现 BaseLLM 接口
   - 通过 LangChain 提供统一的 LLM 提供者接口
   - 支持：`generate()`, `generate_structured()`, `stream_generate()`
   - 通过 `.env` 文件进行配置（LLM_PROVIDER, ZHIPU_API_KEY 等）
   - JSON 解析处理 markdown 代码块、尾随逗号、格式错误的 JSON
   - 使用 StreamingOutput 数据类支持流式输出
   - 基于 LangChain 生态系统

2. **PDFParser** (`src/tools/pdf_parser.py`)
   - 使用 PyPDF2/pdfplumber 解析 PDF 文件
   - 提取文本、结构、元数据

3. **CodeExecutor** (`src/tools/code_executor.py`)
   - 在指定的 conda 环境中执行代码
   - 捕获 stdout/stderr、执行时间
   - 可用 psutil 时支持资源监控（CPU、内存）
   - 改进的超时控制

## Configuration

通过 `.env` 文件提供配置（不支持 YAML 配置）：

```bash
# LLM Provider Selection
LLM_PROVIDER=zhipu

# ZhipuAI Configuration
ZHIPU_API_KEY=your_api_key_here
ZHIPU_MODEL=glm-4.7
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4

# Common LLM Configuration
LLM_MAX_TOKENS=128000
LLM_TEMPERATURE=0.7

# Execution
CONDA_ENV_NAME=py12pt
OUTPUT_DIR=./output/generated_code
MAX_RETRIES=3
TIMEOUT_SECONDS=300

# Logging
LOG_LEVEL=INFO
LOG_FILE=./output/logs/multi_agent.log

# PDF Parser Configuration
PDF_PARSER_ENGINE=pdfplumber  # or "PyPDF2"
EXTRACT_FORMULAS=true
EXTRACT_FIGURES=true
```

## Prompt Templates

提示词模板由 `PromptManager`（`src/prompts/__init__.py`）管理，支持两种格式：

### YAML Format (Preferred)

位于 `src/prompts/*.yaml`：
- `algorithm_analyzer.yaml` - 算法提取提示词
- `code_planner.yaml` - 代码规划提示词
- `code_generator.yaml` - 代码生成提示词
- `env_config.yaml` - 环境配置提示词
- `result_verification.yaml` - 结果验证提示词
- `error_repair.yaml` - 错误修复提示词

YAML 格式包含元数据：
```yaml
name: template_name
input_variables: [var1, var2]
output_format:
  field: type
template: |
  Your prompt here with {var1} and {var2}
```

### TXT Format (Legacy)

位于 `prompts/*.txt`：
- `analyzer.txt` - 算法提取提示词
- `planner.txt` - 代码规划提示词
- `generator.txt` - 代码生成提示词

在 agents 中的使用：
```python
from ..prompts import PROMPTS

prompt = PROMPTS.format_template(
    "code_generator",
    algorithm_info=...,
    code_plan=...,
)
```

## Adding New Agents

1. 在 `src/agents/` 中创建新的 agent 类：
`python
from .base import BaseAgent
from typing import Dict, Any

class MyCustomAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("MyCustomAgent", config)
        # Initialize tools

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # Process state
        # Return updated state with current_step updated
        return {**state, "current_step": "my_step_completed"}
```

2. 在 `src/graph/workflow.py` 中添加节点函数：
```python
def my_custom_node(state: PaperState) -> PaperState:
    """LangGraph node for custom agent."""
    from ..agents.my_custom import MyCustomAgent
    agent = MyCustomAgent(config)
    return agent(state)
```

3. 在 `create_workflow()` 中注册节点：
```python
workflow.add_node("my_custom", my_custom_node)
```

4. 添加边到/从你的新节点：
```python
# Add edges to/from your new node
workflow.add_edge("previous_node", "my_custom")
workflow.add_edge("my_custom", "next_node")
```

## Key Design Decisions

- **LangChain and LangGraph ecosystem**: 系统建立在 LangChain 和 LangGraph 框架上，利用其成熟的生态系统进行多智能体编排
- **Agent/Tool layered architecture**: 系统实现能力清晰地划分为 Agent 层（高级决策制定）和 Tool 层（基础能力）
- **LLM abstraction layer**: 新的 `src/llms/` 目录提供抽象基类和流式输出支持
- **Sequential workflow with repair loop**: Agent 按顺序执行，并具有修复执行错误的迭代修复机制
- **Repair logic**: 代码验证失败会触发错误修复（修复问题）或代码重新生成（最多 max_iterations，默认为 5）
- **Structured LLM output**: `generate_structured()` 强制 JSON 输出，并具有强大的解析功能（处理 markdown 块、尾随逗号、格式错误的 JSON）
- **Multi-LLM support via LangChain**: 架构抽象 LLM 提供者选择，目前支持 ZhipuAI
- **Sandboxed execution**: 生成的代码在隔离的 conda 环境中运行以确保安全
- **Configurable output paths**: 输出目录根据时间戳和 PDF 文件名生成，便于组织
- **Dual prompt format support**: `src/prompts/` 中的基于 YAML 的提示词（首选，包含元数据）和 `prompts/` 中的遗留 TXT 提示词
- **High token limit**: LLM_MAX_MAX_TOKENS=128000，支持完整的代码生成而不会中断
- **Resource monitoring**: 当 psutil 可用时，CodeExecutor 现在监控 CPU 和内存使用情况
