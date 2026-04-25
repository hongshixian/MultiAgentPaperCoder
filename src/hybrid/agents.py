"""Sub-agent node functions for the hybrid workflow.

Each node function:
1. Reads metadata from state (paths, error info)
2. Creates a deepagents sub-agent via create_agent()
3. Invokes the sub-agent with a prompt that includes artifact paths
4. Extracts structured output fields and returns state updates
"""

from __future__ import annotations

import logging
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

from .config import Settings
from .prompts import (
    CODE_GENERATION_PROMPT,
    CODE_VERIFICATION_PROMPT,
    DOCUMENT_ANALYSIS_PROMPT,
    ERROR_REPAIR_PROMPT,
)
from .schemas import (
    CodeGenerationResult,
    DocumentAnalysisResult,
    RepairResult,
    VerificationResult,
)
from .state import PaperState
from .tools.artifact_tools import list_files, read_text_file, save_text_file
from .tools.exec_tools import install_requirements, run_python_entrypoint
from .tools.pdf_tools import read_pdf_text

logger = logging.getLogger("papercoder.agents")


def _extract_structured(result: dict[str, Any]) -> Any | None:
    """Extract structured_response from a sub-agent result dict."""
    return result.get("structured_response")


def _extract_last_message(result: dict[str, Any]) -> str:
    """Extract last message content from a sub-agent result dict."""
    messages = result.get("messages", [])
    if messages:
        last = messages[-1]
        content = getattr(last, "content", "")
        if isinstance(content, str):
            return content[:500]
    return ""


# ---------------------------------------------------------------------------
# Node 1: Document Analysis
# ---------------------------------------------------------------------------

def document_analysis_node(state: PaperState, config: dict) -> dict:
    """Read PDF, analyze paper, write analysis file, return metadata."""
    settings: Settings = config["settings"]
    pdf_path = state.get("pdf_path", "")

    agent = create_agent(
        model=settings.build_llm(),
        tools=[read_pdf_text, save_text_file],
        system_prompt=DOCUMENT_ANALYSIS_PROMPT,
        response_format=DocumentAnalysisResult,
        name="document-analyst",
    )

    prompt = (
        f"请分析以下论文并提取复现所需信息。\n"
        f"PDF路径: {pdf_path}\n"
        f"请将分析结果写入: {settings.paper_analysis_path}"
    )
    logger.info("Invoking document-analyst for %s", pdf_path)

    try:
        result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
    except Exception as exc:
        logger.exception("document-analyst failed")
        return {
            "analysis_status": "failed",
            "errors": state.get("errors", []) + [f"[document-analyst] {exc}"],
        }

    structured = _extract_structured(result)
    if structured is None:
        logger.warning("document-analyst returned no structured_response")
        return {
            "analysis_status": "failed",
            "errors": state.get("errors", []) + [
                f"[document-analyst] 无结构化输出: {_extract_last_message(result)}"
            ],
        }

    return {
        "analysis_path": structured.artifact_path,
        "analysis_status": "completed",
    }


# ---------------------------------------------------------------------------
# Node 2: Code Generation
# ---------------------------------------------------------------------------

def code_generation_node(state: PaperState, config: dict) -> dict:
    """Read analysis, generate code files, return metadata."""
    settings: Settings = config["settings"]
    analysis_path = state.get("analysis_path", "")

    agent = create_agent(
        model=settings.build_llm(),
        tools=[save_text_file, read_text_file, list_files],
        system_prompt=CODE_GENERATION_PROMPT,
        response_format=CodeGenerationResult,
        name="code-generator",
    )

    prompt = (
        f"请读取论文分析报告并生成可运行的Python项目。\n"
        f"分析报告路径: {analysis_path}\n"
        f"代码输出目录: {settings.generated_code_dir}\n"
        f"请先读取分析报告，再生成代码。必须至少生成 main.py 和 requirements.txt。"
    )
    logger.info("Invoking code-generator for %s", settings.generated_code_dir)

    try:
        result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
    except Exception as exc:
        logger.exception("code-generator failed")
        return {
            "generation_status": "failed",
            "errors": state.get("errors", []) + [f"[code-generator] {exc}"],
        }

    structured = _extract_structured(result)
    if structured is None:
        logger.warning("code-generator returned no structured_response")
        return {
            "generation_status": "failed",
            "errors": state.get("errors", []) + [
                f"[code-generator] 无结构化输出: {_extract_last_message(result)}"
            ],
        }

    return {
        "code_dir": structured.code_dir,
        "file_list": structured.files_written,
        "generation_status": "completed",
    }


# ---------------------------------------------------------------------------
# Node 3: Code Verification
# ---------------------------------------------------------------------------

def code_verification_node(state: PaperState, config: dict) -> dict:
    """Install deps, run code, analyze output, return structured result."""
    settings: Settings = config["settings"]
    code_dir = state.get("code_dir", str(settings.generated_code_dir))

    agent = create_agent(
        model=settings.build_llm(),
        tools=[run_python_entrypoint, install_requirements, read_text_file, list_files],
        system_prompt=CODE_VERIFICATION_PROMPT,
        response_format=VerificationResult,
        name="code-verifier",
    )

    prompt = (
        f"请验证以下生成的代码项目。\n"
        f"代码目录: {code_dir}\n"
        f"步骤：先 install_requirements 安装依赖，再 run_python_entrypoint 执行代码，"
        f"然后根据执行输出返回结构化验证结果。"
    )
    logger.info("Invoking code-verifier for %s", code_dir)

    try:
        result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
    except Exception as exc:
        logger.exception("code-verifier failed")
        return {
            "verification_passed": False,
            "error_type": "runtime_error",
            "error_cause": str(exc),
            "error_location": "unknown",
            "stdout_summary": "",
            "needs_repair": True,
            "errors": state.get("errors", []) + [f"[code-verifier] {exc}"],
        }

    structured = _extract_structured(result)
    if structured is None:
        logger.warning("code-verifier returned no structured_response, defaulting to needs_repair")
        return {
            "verification_passed": False,
            "error_type": "logic_error",
            "error_cause": "验证子Agent未返回结构化输出",
            "error_location": "unknown",
            "stdout_summary": "",
            "needs_repair": True,
        }

    return {
        "verification_passed": structured.passed,
        "error_type": structured.error_type,
        "error_cause": structured.error_cause,
        "error_location": structured.error_location,
        "stdout_summary": structured.stdout_summary,
        "needs_repair": structured.needs_repair,
    }


# ---------------------------------------------------------------------------
# Node 4: Error Repair
# ---------------------------------------------------------------------------

def error_repair_node(state: PaperState, config: dict) -> dict:
    """Read error info, fix code, return metadata."""
    settings: Settings = config["settings"]
    code_dir = state.get("code_dir", str(settings.generated_code_dir))
    error_cause = state.get("error_cause", "")
    error_location = state.get("error_location", "unknown")
    error_type = state.get("error_type", "runtime_error")

    agent = create_agent(
        model=settings.build_llm(),
        tools=[read_text_file, save_text_file, list_files],
        system_prompt=ERROR_REPAIR_PROMPT,
        response_format=RepairResult,
        name="error-repairer",
    )

    prompt = (
        f"请修复以下代码项目中的错误。\n"
        f"代码目录: {code_dir}\n"
        f"错误类型: {error_type}\n"
        f"错误原因: {error_cause}\n"
        f"错误位置: {error_location}\n"
        f"请先读取相关文件，分析问题，然后修复代码。"
    )
    iteration = state.get("iteration_count", 0)
    logger.info("Invoking error-repairer (iteration %d) for %s", iteration, code_dir)

    try:
        result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
    except Exception as exc:
        logger.exception("error-repairer failed")
        return {
            "repair_status": "failed",
            "errors": state.get("errors", []) + [f"[error-repairer] {exc}"],
        }

    structured = _extract_structured(result)
    if structured is None:
        logger.warning("error-repairer returned no structured_response")
        return {
            "repair_status": "failed",
            "errors": state.get("errors", []) + [
                f"[error-repairer] 无结构化输出: {_extract_last_message(result)}"
            ],
        }

    return {
        "repair_status": "completed",
        "files_modified": structured.files_modified,
    }
