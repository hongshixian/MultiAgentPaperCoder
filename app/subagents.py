"""Subagent definitions for the DeepAgents implementation."""

from __future__ import annotations

from langchain.agents import create_agent

from app.config import Settings
from app.prompts import (
    CODE_GENERATOR_PROMPT,
    DOCUMENT_ANALYST_PROMPT,
    REPAIR_PROMPT,
    VERIFIER_PROMPT,
)
from app.schemas import PaperAnalysis, RepairPlan, VerificationReport
from app.tools.artifact_tools import list_files, read_text_file, save_text_file
from app.tools.exec_tools import check_entrypoint_exists, python_syntax_check
from app.tools.pdf_tools import read_pdf_text


def _build_compiled_subagent(
    *,
    settings: Settings,
    name: str,
    description: str,
    system_prompt: str,
    tools: list,
    response_format=None,
) -> dict:
    kwargs = {
        "model": settings.build_llm(),
        "tools": tools,
        "system_prompt": system_prompt,
        "name": name,
    }
    if response_format is not None:
        kwargs["response_format"] = response_format

    runnable = create_agent(**kwargs)
    return {
        "name": name,
        "description": description,
        "runnable": runnable,
    }


def build_subagents(settings: Settings) -> list[dict]:
    """Build the paper reproduction subagents."""
    return [
        _build_compiled_subagent(
            settings=settings,
            name="document-analyst",
            description="Reads a paper PDF and extracts structured reproduction requirements",
            system_prompt=DOCUMENT_ANALYST_PROMPT,
            tools=[read_pdf_text, save_text_file],
            response_format=PaperAnalysis,
        ),
        _build_compiled_subagent(
            settings=settings,
            name="code-generator",
            description="Generates the project skeleton and source files for reproduction",
            system_prompt=CODE_GENERATOR_PROMPT,
            tools=[save_text_file, read_text_file, list_files],
        ),
        _build_compiled_subagent(
            settings=settings,
            name="code-verifier",
            description="Runs deterministic checks on generated project files",
            system_prompt=VERIFIER_PROMPT,
            tools=[list_files, read_text_file, check_entrypoint_exists, python_syntax_check],
            response_format=VerificationReport,
        ),
        _build_compiled_subagent(
            settings=settings,
            name="error-repairer",
            description="Analyzes verification failures and repairs the generated project",
            system_prompt=REPAIR_PROMPT,
            tools=[read_text_file, save_text_file, list_files],
            response_format=RepairPlan,
        ),
    ]
