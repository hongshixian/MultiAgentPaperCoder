# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Running the Application

```bash
# Basic usage - process a PDF paper
python -m src.hybrid.main --pdf path/to/paper.pdf

# Specify output directory
python -m src.hybrid.main --pdf paper.pdf --output-dir ./output

# Set max repair iterations (default: 5)
python -m src.hybrid.main --pdf paper.pdf --max-iterations 10

# Enable debug logging (shows LLM requests/responses)
python -m src.hybrid.main --pdf paper.pdf --log-level debug
```

### Running Tests

```bash
# Run all tests with pytest
pytest test_cases/

# Run specific test file
pytest test_cases/unit/test_hybrid.py

# Run with verbose output
pytest test_cases/ -v

# Run specific test
pytest test_cases/unit/test_hybrid.py::TestRouter::test_needs_repair_below_max
```

### Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment (copy and edit .env.example)
cp .env.example .env
```

## Architecture Overview

MultiAgentPaperCoder is a **hybrid architecture** that combines:
- **LangGraph** for deterministic workflow orchestration and state management
- **LangChain agents** for sub-agent specialization (similar to deepagents subagents)
- **Structured logging** with LangChain callbacks for observability

The system automates reproduction of research paper code through a sequential workflow with iterative repair.

### Hybrid Architecture

The implementation lives in `src/hybrid/` and follows this layered structure:

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

### Workflow Orchestration

**PaperCoderWorkflow** (`src/hybrid/workflow.py`) uses LangGraph StateGraph:

- **4 nodes**: `document_analysis`, `code_generation`, `code_verification`, `error_repair`
- **Conditional routing**: `should_continue_verification()` decides next step based on state
- **Iterative repair**: Up to `max_iterations` (default: 5) repair loops
- **State-driven execution**: All nodes read from and update `PaperState`

**Workflow flow:**
```
start → document_analysis → code_generation → code_verification
                                            ↓
code_verification (needs_repair) → error_repair → code_verification ↗
code_verification (failed) → end
code_verification (passed) → end
```

### Sub-Agent Nodes

Each node in `src/hybrid/agents.py` creates a LangChain agent with specific tools and schemas:

1. **document-analyst**: Reads PDF, extracts paper structure, saves analysis
2. **code-generator**: Generates Python project from analysis
3. **code-verifier**: Installs deps, runs code, validates output
4. **error-repairer**: Analyzes errors, fixes code files

All sub-agents return structured output via Pydantic schemas (`schemas.py`).

### State Management

**PaperState** (`src/hybrid/state.py`) is a `TypedDict` passed between nodes:

**Input fields:**
- `pdf_path`: Path to the PDF paper

**Result fields:**
- `analysis_path`: Path to paper analysis markdown
- `analysis_status`: "completed" or "failed"
- `code_dir`: Directory containing generated code
- `file_list`: List of generated files
- `generation_status`: "completed" or "failed"
- `verification_passed`: Boolean
- `error_type`: "none", "import_error", "runtime_error", "logic_error"
- `error_cause`: Error description
- `error_location`: File and line number
- `stdout_summary`: Execution output summary
- `needs_repair`: Boolean
- `repair_status`: "completed" or "failed"
- `files_modified`: List of modified files

**Control fields:**
- `iteration_count`: Current repair iteration
- `max_iterations`: Max repair iterations (default: 5)
- `errors`: Accumulated error messages

## Configuration

Configure via `.env` file:

```bash
# LLM Configuration
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
MODEL_NAME=glm-4.7

# Output
OUTPUT_ROOT=./output
```

**Settings** (`src/hybrid/config.py`) provides:
- `build_llm()`: Creates ChatOpenAI instance with configured settings
- `ensure_dirs()`: Creates output/artifacts/generated_code/logs directories
- `create_run_output_root()`: Creates timestamped run directory

## Logging

The system has two logging layers:

1. **Console logging** (`src/hybrid/logging_utils.py`):
   - Controlled by `--log-level` CLI argument
   - `info`: Shows agent/node/tool calls (default)
   - `debug`: Adds LLM requests/responses

2. **Structured callbacks** (`src/hybrid/callbacks.py`):
   - `PapercoderCallbackHandler` captures LangChain agent/tool events
   - Logs "Agent正在思考..." on LLM calls
   - Logs tool invocations and results
   - Integrated into all sub-agent nodes

3. **File logging**:
   - All logs written to `{run_dir}/logs/papercoder_{timestamp}.log`
   - File logs always capture DEBUG level regardless of console setting

## Tool Layer

Tools are in `src/hybrid/tools/`:

### PDF Tools (`pdf_tools.py`)
- `read_pdf_text(path)`: Extracts text from PDF

### Artifact Tools (`artifact_tools.py`)
- `save_text_file(path, content)`: Writes file (path must stay under OUTPUT_ROOT)
- `read_text_file(path)`: Reads file content
- `list_files(root_dir)`: Lists files recursively

### Exec Tools (`exec_tools.py`)
- `python_syntax_check(root_dir)`: Validates Python syntax
- `check_entrypoint_exists(root_dir)`: Checks for main.py
- `install_requirements(root_dir)`: Installs from requirements.txt
- `run_python_entrypoint(root_dir)`: Executes main.py

## Adding New Sub-Agents

1. Define Pydantic schema in `schemas.py`:
```python
from pydantic import BaseModel, Field

class MyAgentResult(BaseModel):
    field_name: str = Field(description="Description")
```

2. Add system prompt to `prompts.py`:
```python
MY_AGENT_PROMPT = "You are a specialized agent for..."
```

3. Create node function in `agents.py`:
```python
def my_agent_node(state: PaperState, config: dict) -> dict:
    settings: Settings = config["settings"]
    
    agent = create_agent(
        model=settings.build_llm(),
        tools=[/* relevant tools */],
        system_prompt=MY_AGENT_PROMPT,
        response_format=MyAgentResult,
        name="my-agent",
    )
    
    result = agent.invoke(
        {"messages": [HumanMessage(content="Your prompt")]},
        config={"callbacks": [PapercoderCallbackHandler()]},
    )
    
    structured = _extract_structured(result)
    return { /* state updates */ }
```

4. Register node in `workflow.py`:
```python
workflow.add_node("my_agent", my_agent_node)
```

5. Add edges and routing logic as needed

## Key Design Decisions

- **Hybrid over pure LangGraph or pure DeepAgents**: Combines LangGraph's deterministic state management with LangChain agents' flexibility
- **State-driven workflow**: All decisions based on TypedDict state, not hidden state
- **Structured sub-agent output**: All sub-agents return Pydantic schemas for type safety
- **Sandboxed file writes**: `save_text_file` enforces OUTPUT_ROOT boundary
- **Callback-based logging**: PapercoderCallbackHandler provides visibility into agent/tool calls
- **Deterministic router**: `should_continue_verification` has no LLM, pure logic
- **Repair loop with max iterations**: Prevents infinite loops during error repair
- **Two-level logging**: Console (configurable) + file (always DEBUG)
