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
│  │     超级智能体（全局调度、任务分配、异常处理）       │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                     第三层：Agent 层                    │
│  ┌──────────────────┐  ┌──────────────────┐        │
│  │  文档分析智能体   │  │  代码生成智能体   │        │
│  └──────────────────┘  └──────────────────┘        │
│  ┌──────────────────┐  ┌──────────────────┐        │
│  │  代码验证智能体   │  │  错误修复智能体   │        │
│  └──────────────────┘  └──────────────────┘        │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                     第四层：Tool 层                     │
│  ┌──────────────────┐  ┌──────────────────┐        │
│  │  PDF 解析工具     │  │  代码执行工具     │        │
│  └──────────────────┘  └──────────────────┘        │
│  ┌──────────────────┐  ┌──────────────────┐        │
│  │  大语言模型接口   │  │  领域知识库      │        │
│  └──────────────────┘  └──────────────────┘        │
└─────────────────────────────────────────────────────────┘
```

### Agent Layer

All agents inherit from `BaseAgent` (`src/agents/base.py`) and implement the `__call__` method that receives and returns a `PaperState` dictionary.

1. **超级智能体** (`src/agents/super_agent.py`)
   - Coordinates workflow execution (actual coordination in workflow.py)
   - Provides status reporting

2. **文档分析智能体** (`src/agents/pdf_reader.py`, `src/agents/algorithm_analyzer.py`)
   - Reads and parses PDF files
   - Extracts text, structure, metadata
   - Analyzes paper content to extract algorithm details
   - Uses LLM to understand algorithm logic, hyperparameters, requirements
   - Returns structured algorithm analysis

3. **代码生成智能体** (`src/agents/code_planner.py`, `src/agents/code_generator.py`)
   - Designs project structure based on algorithm analysis
   - Plans file organization, implementation steps, dependencies
   - Generates complete Python code files
   - Analyzes code dependencies and generates requirements.txt
   - Uses LLM for architectural decisions and code generation

4. **代码验证智能体** (`src/agents/code_validator.py`, `src/agents/result_verification_agent.py`)
   - Executes generated code in isolated conda environment
   - Monitors execution, captures errors, provides fix suggestions
   - Verifies execution results meet expected outcomes
   - Assesses quality of generated code execution
   - Uses CodeExecutor tool

5. **错误修复智能体** (`src/agents/error_repair_agent.py`)
   - Analyzes errors from validation
   - Generates fixes for identified issues
   - Updates code files with repairs

### Workflow Orchestration

**PaperCoderWorkflow** (`src/graph/workflow.py`) orchestrates sequential execution with iterative repair:
- Creates initial state with `PaperState` structure
- Determines next step based on current state, errors, and verification results
- Handles retry logic with iteration counter (max_iterations, default: 5)
- Generates execution summaries

**Workflow flow:**
```
start → 文档分析 → 代码生成 → 代码验证
                          ↓
代码验证 (需要修复) → 错误修复 → 代码验证 ↗
```

### State Management

**PaperState** (`src/state/__init__.py`) is a TypedDict that flows through the workflow:

**Input fields:**
- `pdf_path`: Path to the PDF file

**Result fields:**
- `paper_content`: PDF parsing result
- `algorithm_analysis`: Algorithm extraction result
- `code_plan`: Code planning result
- `generated_code`: Generated code metadata
- `verification_result`: Result quality assessment
- `repair_history`: List of repair attempts

**Control fields:**
- `current_step`: Current workflow step
- `errors`: Accumulated error messages
- `iteration_count`: Current iteration for repair loop
- `max_iterations`: Maximum iterations for repair loop (default: 5)

### Tool Layer

1. **LLMClient** (`src/tools/llm_client.py`)
   - Unified interface for ZhipuAI APIs via LangChain
   - Supports: `generate()`, `generate_structured()` with JSON parsing, `stream_generate()`
   - Configuration via `.env` file (LLM_PROVIDER, ZHIPU_API_KEY, etc.)
   - JSON parsing handles markdown code blocks, trailing commas, malformed JSON
   - Based on LangChain ecosystem

2. **PDFParser** (`src/tools/pdf_parser.py`)
   - Parses PDF files using PyPDF2/pdfplumber
   - Extracts text, structure, metadata

3. **CodeExecutor** (`src/tools/code_executor.py`)
   - Executes code in specified conda environment
   - Captures stdout/stderr, execution time

## Configuration

Configuration is provided through `.env` file:

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

Prompt templates are managed by `PromptManager` (`src/prompts/__init__.py`) which supports two formats:

### YAML Format (Preferred)

Located in `src/prompts/*.yaml`:
- `algorithm_analyzer.yaml` - Algorithm extraction prompts
- `code_planner.yaml` - Code planning prompts
- `code_generator.yaml` - Code generation prompts
- `env_config.yaml` - Environment configuration prompts
- `result_verification.yaml` - Result verification prompts
- `error_repair.yaml` - Error repair prompts

YAML format includes metadata:
```yaml
name: template_name
input_variables: [var1, var2]
output_format:
  field: type
template: |
  Your prompt here with {var1} and {var2}
```

### TXT Format (Legacy)

Located in `prompts/*.txt`:
- `analyzer.txt` - Algorithm extraction prompts
- `planner.txt` - Code planning prompts
- `generator.txt` - Code generation prompts

Usage in agents:
```python
from ..prompts import PROMPTS

prompt = PROMPTS.format_template(
    "code_generator",
    algorithm_info=...,
    code_plan=...,
)
```

## Adding New Agents

1. Create new agent class in `src/agents/`:
```python
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

2. Register agent in `src/graph/workflow.py`:
```python
from ..agents.my_custom import MyCustomAgent

# In __init__:
self.my_custom_agent = MyCustomAgent(self.config)
```

3. Add routing logic in `_determine_next_step()`:
```python
elif current_step == "previous_step_completed":
    return "my_custom_step"
```

4. Add execution logic in `run()`:
```python
elif next_step == "my_custom_step":
    state = self.my_custom_agent(state)
```

## Key Design Decisions

- **LangChain and LangGraph ecosystem**: The system is built on LangChain and LangGraph framework, leveraging their mature ecosystem for multi-agent orchestration
- **Agent/Tool layered architecture**: System implementation capability is clearly divided into Agent layer (high-level decision making) and Tool layer (basic capabilities)
- **Sequential workflow with repair loop**: Agents execute in order with an iterative repair mechanism for fixing execution errors
- **Repair logic**: Code verification failures trigger either error repair (fix issues) or code regeneration (up to max_iterations, default: 5)
- **Structured LLM output**: `generate_structured()` enforces JSON output with robust parsing (handles markdown blocks, trailing commas, malformed JSON)
- **Multi-LLM support via LangChain**: Architecture abstracts LLM provider selection, currently supports ZhipuAI
- **Sandboxed execution**: Generated code runs in isolated conda environment for safety
- **Configurable output paths**: Output directories are generated with timestamps and PDF filenames for organization
- **Dual prompt format support**: YAML-based prompts in `src/prompts/` (preferred, with metadata) and legacy TXT prompts in `prompts/`
- **High token limit**: LLM_MAX_TOKENS=128000 to support complete code generation without interruption
