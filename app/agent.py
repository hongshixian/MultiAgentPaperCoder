"""DeepAgents app builder."""

from __future__ import annotations

from app.config import Settings
from app.prompts import MAIN_SYSTEM_PROMPT
from app.subagents import build_subagents
from app.tools.artifact_tools import list_files, read_text_file, save_text_file
from app.tools.exec_tools import check_entrypoint_exists, python_syntax_check
from app.tools.pdf_tools import read_pdf_text


def build_agent(settings: Settings):
    """Create the DeepAgents orchestrator lazily."""
    try:
        from deepagents import create_deep_agent
    except ImportError as exc:
        raise ImportError(
            "deepagents is not installed. Install project requirements before running the DeepAgents entrypoint."
        ) from exc

    settings.ensure_dirs()

    tools = [
        read_pdf_text,
        save_text_file,
        read_text_file,
        list_files,
        check_entrypoint_exists,
        python_syntax_check,
    ]

    return create_deep_agent(
        model=settings.build_llm(),
        tools=tools,
        system_prompt=MAIN_SYSTEM_PROMPT,
        subagents=build_subagents(),
        name="papercoder-main",
    )
