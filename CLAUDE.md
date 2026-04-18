# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Running the Application

```bash
# Basic usage - process a PDF paper
python -m src.main --pdf path/to/paper.pdf

# With custom configuration file
python -m src.main --pdf paper.pdf --config config/custom.yaml

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

MultiAgentPaperCoder is a multi-agent system that automates the reproduction of research paper code. The system follows a sequential workflow through specialized agents with an iterative repair mechanism.

### Agent Layer

All agents inherit from `BaseAgent` (src/agents/base.py) and implement the `__call__` method that receives and returns a `PaperState` dictionary.

1. **PDFReaderAgent** (`src/agents/pdf_reader.py`)
   - Reads and parses PDF files
   - Extracts text, structure, metadata
   - Uses PDFParser tool

2. **AlgorithmAnalyzerAgent** (`src/agents/algorithm_analyzer.py`)
   - Analyzes paper content to extract algorithm details
   - Uses LLM to understand algorithm logic, hyperparameters, requirements
   - Returns structured algorithm analysis

3. **CodePlannerAgent** (`src/agents/code_planner.py`)
   - Designs project structure based on algorithm analysis
   - Plans file organization, implementation steps, dependencies
   - Uses LLM for architectural decisions

4. **CodeGeneratorAgent** (`src/agents/code_generator.py`)
   - Generates complete Python code files
   - Writes files to output directory
   - Uses LLM for code generation with structured JSON output

5. **EnvConfigAgent** (`src/agents/env_config_agent.py`)
   - Validates and configures the execution environment
   - Checks conda environment availability
   - Sets up dependencies

6. **CodeValidatorAgent** (`src/agents/code_validator.py`)
   - Executes generated code in isolated conda environment
   - Monitors execution, captures errors, provides fix suggestions
   - Uses CodeExecutor tool

7. **ResultVerificationAgent** (`src/agents/result_verification_agent.py`)
   - Verifies execution results meet expected outcomes
   - Assesses quality of generated code execution
   - Determines if repair or regeneration is needed

8. **ErrorRepairAgent** (`src/agents/error_repair_agent.py`)
   - Analyzes errors from validation
   - Generates fixes for identified issues
   - Updates code files with repairs

9. **PaperCoderSuperAgent** (`src/agents/super_agent.py`)
   - Coordinates workflow (mostly symbolic; actual coordination is in workflow.py)
   - Provides status reporting

### Workflow Orchestration

**PaperCoderWorkflow** (`src/graph/workflow.py`) orchestrates the sequential execution with iterative repair:
- Creates initial state with `PaperState` structure
- Determines next step based on current state, errors, and verification results
- Handles retry logic with iteration counter (max_iterations, default: 5)
- Generates execution summaries

**Workflow flow:**
```
start → pdf_reading → algorithm_analysis → code_planning → code_generation → env_config → validation → result_verification
                                                                                                                    ↓
result_verification (needs_repair) → error_repair → validation ↗
result_verification (needs_regeneration) → code_generation ↗
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
- `env_config`: Environment configuration result
- `validation_result`: Code execution validation result
- `verification_result`: Result quality assessment
- `repair_history`: List of repair attempts

**Control fields:**
- `current_step`: Current workflow step
- `errors`: Accumulated error messages
- `retry_count`: Retry counter (legacy)
- `max_retries`: Maximum retry attempts (default: 3)
- `iteration_count`: Current iteration for repair loop
- `max_iterations`: Maximum iterations for repair loop (default: 5)

### Tool Layer

1. **LLMClient** (`src/tools/llm_client.py`)
   - Unified interface for both Claude and ZhipuAI APIs via LangChain
   - Supports: `generate()`, `generate_structured()` with JSON parsing, `stream_generate()`
   - Configuration via `.env` file (LLM_PROVIDER, ANTHROPIC_API_KEY, ZHIPU_API_KEY, etc.)
   - JSON parsing handles markdown code blocks, trailing commas, malformed JSON

2. **PDFParser** (`src/tools/pdf_parser.py`)
   - Parses PDF files using PyPDF2/pdfplumber
   - Extracts text, structure, metadata

3. **CodeExecutor** (`src/tools/code_executor.py`)
   - Executes code in specified conda environment
   - Captures stdout/stderr, execution time

## Configuration

Configuration can be provided through multiple sources (priority order: CLI args > YAML config > .env file > defaults):

### YAML Configuration (`config/default.yaml`)

```yaml
llm:
  provider: zhipu  # or "claude"
  claude:
    model: claude-3-5-sonnet-20241022
  zhipu:
    model: glm-5
    base_url: https://open.bigmodel.cn/api/paas/v4
  max_tokens: 4096
  temperature: 0.7

execution:
  conda_env: py12pt
  output_dir: ./output
  max_retries: 3
  timeout_seconds: 300

logging:
  level: INFO  # DEBUG, INFO, WARNING, ERROR
```

### Environment Variables (`.env`)

```bash
# LLM Provider Selection
LLM_PROVIDER=claude  # or "zhipu"

# Claude Configuration
ANTHROPIC_API_KEY=your_key
CLAUDE_MODEL=claude-3-5-sonnet-20241022

# ZhipuAI Configuration
ZHIPU_API_KEY=your_key
ZHIPU_MODEL=glm-5
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4

# Common LLM Configuration
LLM_MAX_TOKENS=4096
LLM_TEMPERATURE=0.7

# Execution
CONDA_ENV_NAME=py12pt
OUTPUT_DIR=./output/generated_code
MAX_RETRIES=3
TIMEOUT_SECONDS=300
ENABLE_CACHE=true

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

- **Sequential workflow with repair loop**: Agents execute in order with an iterative repair mechanism for fixing execution errors
- **Repair logic**: Result verification failures trigger either error repair (fix issues) or code regeneration (up to max_iterations, default: 5)
- **Structured LLM output**: `generate_structured()` enforces JSON output with robust parsing (handles markdown blocks, trailing commas, malformed JSON)
- **Multi-LLM support via LangChain**: Architecture abstracts LLM provider selection (Claude via LangChain-Anthropic or ZhipuAI via OpenAI-compatible API)
- **Dual prompt format support**: YAML-based prompts in `src/prompts/` (preferred, with metadata) and legacy TXT prompts in `prompts/`
- **Sandboxed execution**: Generated code runs in isolated conda environment for safety
- **Configurable output paths**: Output directories are generated with timestamps and PDF filenames for organization
