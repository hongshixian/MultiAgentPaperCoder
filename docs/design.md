# MultiAgentPaperCoder 设计文档

## 概述

MultiAgentPaperCoder 是一个基于多智能体系统的自动化论文代码复现工具。该系统能够读取算法论文，理解算法实现，规划复现方案，生成可运行代码，并验证代码的正确性。系统采用**混合架构**：使用 LangGraph 进行确定性工作流编排，使用 LangChain Agents 实现子智能体专业化。

## 核心目标

1. 自动化论文算法代码复现流程
2. 降低论文复现的门槛
3. 提供代码生成的可追溯性和可解释性

## 技术栈

| 组件 | 技术选择 | 版本要求 |
|------|----------|----------|
| 开发语言 | Python 3.12+ |  |
| 大语言模型 | 智谱AI GLM-4.7 (OpenAI 兼容) | 最新版本 |
| 工作流编排 | LangGraph | >=1.1.0 |
| 子智能体框架 | LangChain Agents | >=0.2.0 |
| PDF解析 | PyPDF2 | 最新版本 |
| 数据验证 | Pydantic | >=2.0.0 |
| 环境管理 | python-dotenv | >=1.0.0 |

**技术决策说明**：选择**混合架构**而非纯 LangGraph 或纯 DeepAgents：
- LangGraph 的 StateGraph 提供确定性的状态管理和路由
- LangChain Agents 提供灵活的工具调用和结构化输出
- 这种结合在保留工作流控制力的同时，获得了子智能体的灵活性

### 混合架构图

```
┌─────────────────────────────────────────────────────────┐
│                   CLI Layer (main.py)                    │
│  ┌───────────────────────────────────────────────────┐  │
│  │        Argument parsing, logging setup           │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│              LangGraph Workflow Layer                    │
│  ┌───────────────────────────────────────────────────┐  │
│  │    StateGraph with 4 nodes + conditional routing │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│              Sub-Agent Nodes (agents.py)                 │
│  ┌──────────────────┐  ┌────────────────┐  ┌──────────────┐  │
│  │ document-analyst │  │ code-generator │  │ code-verifier │  │
│  └──────────────────┘  └────────────────┘  └──────────────┘  │
│  ┌──────────────────────────────────────────────┐           │
│  │            error-repairer                     │           │
│  └──────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                   Tool Layer (tools/)                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────┐  │
│  │   pdf_tools      │  │  artifact_tools  │  │ exec_  │  │
│  │   read_pdf_text  │  │  save/read/list  │  │ tools  │  │
│  └──────────────────┘  └──────────────────┘  └────────┘  │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│              LLM Layer (config.py)                       │
│  ┌───────────────────────────────────────────────────┐  │
│  │   ChatOpenAI via OpenAI-compatible API (ZhipuAI) │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## 子智能体节点设计

### 1. 文档分析智能体（document-analyst）

**角色**：document reader & algorithm extractor

**职责**：
- 调用 PDF 解析工具解析 PDF 论文
- 提取论文结构化信息
- 保存分析结果到文件

**能力（工具）**：
- `read_pdf_text`: PDF 文本提取（PyPDF2）
- `save_text_file`: 保存分析报告

**结构化输出**（`DocumentAnalysisResult`）：
```python
{
    "title": str,                    # 论文标题
    "problem": str,                  # 解决的问题
    "method_summary": str,           # 方法概述
    "modules_to_implement": list[str],  # 需要实现的模块
    "training_flow": list[str],     # 训练流程
    "evaluation_flow": list[str],    # 评估流程
    "dependencies": list[str],       # Python 依赖
    "risks": list[str],             # 复现风险
    "artifact_path": str,           # 分析报告保存路径
}
```

**实现文件**：`src/hybrid/agents.py` - `document_analysis_node()`

### 2. 代码生成智能体（code-generator）

**角色**：code architect & code writer

**职责**：
- 根据算法分析结果设计代码结构
- 生成完整的 Python 项目骨架
- 生成 requirements.txt

**能力（工具）**：
- `save_text_file`: 保存代码文件
- `read_text_file`: 读取已有文件
- `list_files`: 列出项目文件

**结构化输出**（`CodeGenerationResult`）：
```python
{
    "files_written": list[str],    # 生成的文件列表
    "entry_point": str,            # 入口文件
    "summary": str,                # 生成摘要
    "code_dir": str               # 代码目录
}
```

**实现文件**：`src/hybrid/agents.py` - `code_generation_node()`

### 3. 代码验证智能体（code-verifier）

**角色**：code tester & result evaluator

**职责**：
- 安装项目依赖（`install_requirements`）
- 执行代码入口点（`run_python_entrypoint`）
- 分析执行输出
- 判断验证结果

**能力（工具）**：
- `install_requirements`: 安装 requirements.txt
- `run_python_entrypoint`: 执行 main.py
- `read_text_file`: 读取代码文件
- `list_files`: 列出项目文件

**结构化输出**（`VerificationResult`）：
```python
{
    "passed": bool,               # 是否通过验证
    "error_type": str,            # 错误类型（none/import_error/runtime_error/logic_error）
    "error_cause": str,           # 错误原因
    "error_location": str,        # 错误位置
    "stdout_summary": str,        # 执行输出摘要
    "needs_repair": bool          # 是否需要修复
}
```

**实现文件**：`src/hybrid/agents.py` - `code_verification_node()`

### 4. 错误修复智能体（error-repairer）

**角色**：code debugger

**职责**：
- 分析错误信息
- 定位代码问题
- 修复相关文件

**能力（工具）**：
- `read_text_file`: 读取代码文件
- `save_text_file`: 保存修复后的文件
- `list_files`: 列出项目文件

**结构化输出**（`RepairResult`）：
```python
{
    "files_modified": list[str],  # 修改的文件列表
    "repair_summary": str,        # 修复摘要
    "root_cause": str            # 根本原因
}
```

**实现文件**：`src/hybrid/agents.py` - `error_repair_node()`

## Tool 设计

### 1. PDF 工具（pdf_tools.py）

**技术选型**：PyPDF2

**功能**：
- `read_pdf_text(path)`: 提取 PDF 文本内容

**实现文件**：`src/hybrid/tools/pdf_tools.py`

### 2. 工件工具（artifact_tools.py）

**功能**：
- `save_text_file(path, content)`: 写入文本文件（强制在 OUTPUT_ROOT 内）
- `read_text_file(path)`: 读取文本文件
- `list_files(root_dir)`: 递归列出目录文件

**安全特性**：
- 沙盒限制：`save_text_file` 禁止写入 OUTPUT_ROOT 外的路径

**实现文件**：`src/hybrid/tools/artifact_tools.py`

### 3. 执行工具（exec_tools.py）

**功能**：
- `python_syntax_check(root_dir)`: Python 语法检查
- `check_entrypoint_exists(root_dir)`: 检查 main.py 是否存在
- `install_requirements(root_dir)`: 安装 requirements.txt
- `run_python_entrypoint(root_dir)`: 执行 main.py

**实现文件**：`src/hybrid/tools/exec_tools.py`

## 工作流设计

### 状态定义

```python
from typing import TypedDict, list

class PaperState(TypedDict, total=False):
    # 输入
    pdf_path: str

    # 文档分析结果
    analysis_path: str
    analysis_status: str  # "completed" or "failed"

    # 代码生成结果
    code_dir: str
    file_list: list[str]
    generation_status: str  # "completed" or "failed"

    # 验证结果
    verification_passed: bool
    error_type: str  # "none", "import_error", "runtime_error", "logic_error"
    error_cause: str
    error_location: str
    stdout_summary: str
    needs_repair: bool

    # 错误修复结果
    repair_status: str  # "completed" or "failed"
    files_modified: list[str]

    # 控制字段
    iteration_count: int
    max_iterations: int
    errors: list[str]
```

### 工作流图

```
start → document_analysis → code_generation → code_verification
                                            ↓
code_verification (needs_repair, iteration < max) → error_repair → code_verification ↗
code_verification (needs_repair, iteration >= max) → end
code_verification (passed) → end
code_verification (analysis/generation failed) → end
```

### 决策逻辑

`should_continue_verification(state)` 是纯逻辑函数，无 LLM 参与：

1. **前置检查**：分析或生成失败则直接结束
2. **验证通过**：无需修复，结束
3. **需要修复**：
   - 迭代次数 < 最大迭代次数：进入 error_repair
   - 迭代次数 >= 最大迭代次数：结束（避免无限循环）

## 配置管理

### 环境变量配置（.env）

```bash
# LLM Configuration (OpenAI-compatible API)
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
MODEL_NAME=glm-4.7

# Output
OUTPUT_ROOT=./output
```

### Settings 类（src/hybrid/config.py）

```python
@dataclass
class Settings:
    """Runtime settings for the hybrid implementation."""
    
    openai_api_key: str
    openai_base_url: str
    model_name: str
    output_root: Path
    log_dir_override: str

    @property
    def artifacts_dir(self) -> Path
    @property
    def generated_code_dir(self) -> Path
    @property
    def paper_analysis_path(self) -> Path
    @property
    def log_dir(self) -> Path
    
    def ensure_dirs(self) -> None
    @property
    def resolved_model_name(self) -> str
    def build_llm(self) -> ChatOpenAI
    def create_run_output_root(self, pdf_path: Path, timestamp: datetime | None = None) -> Path
```

## 提示词管理

### 子智能体系统提示词（src/hybrid/prompts.py）

系统提示词使用 Python 模块定义（不再使用 YAML/TXT 文件）：

```python
DOCUMENT_ANALYSIS_PROMPT = """
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

CODE_GENERATION_PROMPT = """
你是代码生成子智能体。

目标：
- 根据论文分析结果生成最小可运行项目
- 优先生成清晰的 Python 项目结构
- 避免一次性写出过度复杂的工程

要求：
- 至少生成 main.py 和 requirements.txt
- 如果无法完整实现，先生成合理骨架和 TODO 注释
"""

CODE_VERIFICATION_PROMPT = """
你是代码验证子智能体。

目标：
- 基于工具检查输出目录中的 Python 代码
- 首先做语法检查
- 然后检查入口文件是否存在
- 最后输出结构化验证报告
"""

ERROR_REPAIR_PROMPT = """
你是错误修复子智能体。

目标：
- 根据验证阶段的错误信息定位问题
- 给出精确修复方案
- 只改必要文件
- 修复后提醒主智能体重新验证
"""
```

## 依赖管理

### Python 依赖（requirements.txt）

```txt
# Core framework
deepagents>=0.5.0
langgraph>=1.1.0
langchain>=0.2.0
langchain-core>=0.2.0
langchain-openai>=0.2.0

# PDF parsing
PyPDF2>=3.0.0

# Data validation and configuration
pydantic>=2.0.0
python-dotenv>=1.0.0
```

## 日志系统

### 双层日志架构

1. **控制台日志**（`setup_console_logging`）:
   - 通过 `--log-level` 参数控制
   - `info`: 显示 agent/node/tool 调用（默认）
   - `debug`: 额外显示 LLM 请求/响应

2. **结构化回调**（`PapercoderCallbackHandler`）:
   - 捕获 LangChain agent/tool 事件
   - INFO: "Agent正在思考...", "Agent调用了工具: xx"
   - DEBUG: LLM 请求提示词和响应内容

3. **文件日志**（`create_run_logger`）:
   - 写入 `{run_dir}/logs/papercoder_{timestamp}.log`
   - 文件日志始终为 DEBUG 级别

## 测试

### 测试用例（test_cases/）

```bash
# 运行所有测试
pytest test_cases/

# 运行单元测试
pytest test_cases/unit/

# 运行特定测试
pytest test_cases/unit/test_hybrid.py::TestRouter::test_needs_repair_below_max
```

### 测试覆盖

- 路由逻辑测试（`TestRouter`）
- 状态字段测试（`TestPaperState`）
- Pydantic schema 测试（`TestSchemas`）
- 工具测试（`TestArtifactTools`, `TestExecTools`）
- 配置测试（`TestSettings`）
- 工作流构建测试（`TestWorkflowBuild`）

## 文档说明

本文档描述 MultiAgentPaperCoder 的混合架构设计，结合了 LangGraph 工作流编排和 LangChain 子智能体专业化的优势。文档将随着项目开发进展持续更新，保持与实际代码实现的一致性。
