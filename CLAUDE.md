# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Running the Application

```bash
# Basic usage - process a PDF paper
python -m src.main --pdf path/to/paper.pdf

# With custom output directory
python -m src.main --pdf paper.pdf --output-dir ./my_output

# Specify conda environment for code validation
python -m src.main --pdf paper.pdf --conda-env py12pt

# Skip code validation step
python -m src.main --pdf paper.pdf --skip-validation

# Enable verbose output
python -m src.main --pdf paper.pdf --verbose
```

### Running Tests

```bash
# Basic functionality tests
python examples/test_simple.py

# Test with actual PDF (requires a PDF file)
python test_with_pdf.py --pdf paper_examples/your_paper.pdf

# Test ZhipuAI integration
python test_zhipu.py

# Test complete workflow
python test_workflow.py
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

MultiAgentPaperCoder is a multi-agent system that automates the reproduction of research paper code. The system follows a sequential workflow through specialized agents:

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

5. **CodeValidatorAgent** (`src/agents/code_validator.py`)
   - Executes generated code in isolated conda environment
   - Monitors execution, captures errors, provides fix suggestions
   - Uses CodeExecutor tool

6. **PaperCoderSuperAgent** (`src/agents/super_agent.py`)
   - Coordinates workflow (mostly symbolic; actual coordination is in workflow.py)
   - Provides status reporting

### Workflow Orchestration

**PaperCoderWorkflow** (`src/graph/workflow.py`) orchestrates the sequential execution:
- Creates initial state with `PaperState` structure
- Determines next step based on current state and errors
- Handles retry logic for failed code generation
- Generates execution summaries

### State Management

**PaperState** (`src/state/__init__.py`) is a TypedDict that flows through the workflow:
- Input: `pdf_path`
- Results: `paper_content`, `algorithm_analysis`, `code_plan`, `generated_code`, `validation_result`
- Control: `current_step`, `errors`, `retry_count`, `max_retries`

### Tool Layer

1. **LLMClient** (`src/tools/llm_client.py`)
   - Unified interface for both Claude and ZhipuAI APIs
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

Configuration is managed through `.env` file:

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

# Execution
CONDA_ENV_NAME=py12pt
OUTPUT_DIR=./output/generated_code
MAX_RETRIES=3
TIMEOUT_SECONDS=300
LLM_MAX_TOKENS=4096
LLM_TEMPERATURE=0.7
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

## Prompt Templates

Prompt templates are stored in `prompts/` directory:
- `analyzer.txt` - Algorithm extraction prompts
- `planner.txt` - Code planning prompts  
- `generator.txt` - Code generation prompts

Agents load these templates via `_load_prompt_template()` with fallback to hardcoded defaults.

## Key Design Decisions

- **Sequential workflow**: Agents execute in order; each agent depends on previous agent's output
- **Retry logic**: Code validation failures trigger retry of code generation (up to max_retries)
- **Structured LLM output**: `generate_structured()` enforces JSON output with robust parsing
- **Multi-LLM support**: Architecture abstracts LLM provider selection
- **Sandboxed execution**: Generated code runs in isolated conda environment for safety
