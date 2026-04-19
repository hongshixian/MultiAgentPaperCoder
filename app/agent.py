"""DeepAgents app builder."""

from __future__ import annotations

from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

from app.config import Settings
from app.prompts import MAIN_SYSTEM_PROMPT
from app.subagents import build_subagents
from app.tools.artifact_tools import list_files, read_text_file, save_text_file
from app.tools.exec_tools import check_entrypoint_exists, python_syntax_check
from app.tools.pdf_tools import read_pdf_text


def build_agent(settings: Settings):
    """Create the DeepAgents orchestrator lazily."""
    try:
        from deepagents.backends import StateBackend
        from deepagents.middleware.patch_tool_calls import PatchToolCallsMiddleware
        from deepagents.middleware.subagents import SubAgentMiddleware
    except ImportError as exc:
        raise ImportError(
            "deepagents is not installed. Install project requirements before running the DeepAgents entrypoint."
        ) from exc

    settings.ensure_dirs()
    backend = StateBackend()

    tools = [
        read_pdf_text,
        save_text_file,
        read_text_file,
        list_files,
        check_entrypoint_exists,
        python_syntax_check,
    ]

    return create_agent(
        model=settings.build_llm(),
        tools=tools,
        system_prompt=MAIN_SYSTEM_PROMPT,
        name="papercoder-main",
        checkpointer=MemorySaver(),
        debug=False,
        middleware=[
            PatchToolCallsMiddleware(),
            SubAgentMiddleware(
                backend=backend,
                subagents=build_subagents(settings),
            ),
        ],
    )
