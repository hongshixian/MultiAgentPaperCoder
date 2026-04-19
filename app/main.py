"""CLI entrypoint for the DeepAgents paper reproduction app."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from typing import Any

from app.agent import build_agent
from app.bootstrap import (
    ensure_minimum_generated_project,
    generate_initial_analysis,
    generate_verification_report,
)
from app.config import Settings
from app.logging_utils import create_run_logger, serialize_for_log


def build_user_prompt(pdf_path: str, output_dir: str) -> str:
    """Build the high-level paper reproduction task prompt."""
    return f"""
Run one paper reproduction workflow with these requirements:

1. A fresh paper analysis for this run has already been written to this exact path: {output_dir}/artifacts/paper_analysis.txt
2. Use the code-generator subagent to create a minimal Python project under this absolute directory: {output_dir}/generated_code/
3. The generated project must include at least:
   - main.py
   - requirements.txt
4. Write main.py and requirements.txt before writing any optional extra modules.
5. Treat this output directory as a brand-new empty workspace for this run. Do not inspect, reuse, or summarize files from any other previous output directory.
6. Never read or reuse generated files from any previous run directory.
7. Use the current run's paper analysis artifact as the source of truth for code generation.
8. Before moving to the next stage, ensure the current stage wrote its required file inside this run directory.
9. Final response must include:
   - paper method summary
   - generated files
   - expected verification considerations
   - unresolved issues and risks
"""


def _print_progress(message: str) -> None:
    """Print concise human-readable progress information."""
    print(f"[progress] {message}")


def _flatten_text(value: Any) -> str:
    """Flatten nested stream payloads into lowercase text for lightweight matching."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.lower()
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_flatten_text(item) for item in value)
    return str(value).lower()


def _stage_from_namespace(namespace: tuple[str, ...]) -> str | None:
    """Infer a coarse workflow stage from the stream namespace."""
    ns_text = "/".join(namespace).lower()
    if "document-analyst" in ns_text:
        return "analysis"
    if "code-generator" in ns_text:
        return "generation"
    if "code-verifier" in ns_text:
        return "verification"
    if "error-repairer" in ns_text:
        return "repair"
    return None


def _task_progress(task_name: str, namespace: tuple[str, ...], task_data: dict[str, Any]) -> str | None:
    """Map low-level task events to concise terminal progress messages."""
    stage = _stage_from_namespace(namespace)
    if task_name == "model" and not namespace:
        return "主智能体正在规划当前步骤"
    if task_name == "tools" and not namespace:
        return "主智能体正在调用工具或分派子智能体"
    if task_name == "model" and stage == "analysis":
        return "文档分析智能体正在整理论文方法"
    if task_name == "model" and stage == "generation":
        return "代码生成智能体正在编写复现骨架"
    if task_name == "model" and stage == "verification":
        return "验证智能体正在检查生成代码"
    if task_name == "model" and stage == "repair":
        return "修复智能体正在分析并修改问题代码"
    if task_name == "tools":
        payload = _flatten_text(task_data)
        if "read_pdf_text" in payload:
            return "正在读取论文 PDF"
        if "paper_analysis.txt" in payload or ("save_text_file" in payload and stage == "analysis"):
            return "正在写入论文分析结果"
        if "verification_report.txt" in payload or ("save_text_file" in payload and stage == "verification"):
            return "正在写入验证报告"
        if "check_entrypoint_exists" in payload or "python_syntax_check" in payload:
            return "正在执行代码验证"
        if "save_text_file" in payload and stage == "generation":
            return "正在落盘生成的代码文件"
    return None


def main() -> None:
    """Parse CLI args and invoke the DeepAgents workflow."""
    parser = argparse.ArgumentParser(description="DeepAgents-based paper reproduction tool")
    parser.add_argument("--pdf", required=True, help="Path to the paper PDF")
    parser.add_argument("--output-dir", default="./output", help="Output directory root")
    args = parser.parse_args()

    pdf_path = Path(args.pdf).resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    base_output_root = Path(args.output_dir).resolve()
    base_settings = Settings(output_root=base_output_root)
    run_output_root = base_settings.create_run_output_root(pdf_path)
    settings = Settings(output_root=run_output_root, log_dir_override=str(base_output_root / "logs"))
    os.environ["OUTPUT_ROOT"] = str(settings.output_root)

    agent = build_agent(settings)
    run_logger, file_handler, log_path, run_id = create_run_logger(settings.log_dir)
    for name in ["papercoder.tools", "papercoder.tools.pdf", "papercoder.tools.artifacts", "papercoder.tools.exec"]:
        tool_logger = logging.getLogger(name)
        tool_logger.setLevel(logging.DEBUG)
        tool_logger.handlers.clear()
        tool_logger.addHandler(file_handler)
        tool_logger.propagate = False
    logging.getLogger().setLevel(logging.WARNING)

    run_logger.debug("Starting agent run %s", run_id)
    run_logger.debug("Resolved PDF path: %s", pdf_path)
    run_logger.debug("Base output root: %s", base_output_root)
    run_logger.debug("Run output root: %s", settings.output_root)
    run_logger.debug("Log file: %s", log_path)
    print(f"Logging agent execution to {log_path}")
    print(f"Run output directory: {settings.output_root}")
    _print_progress("正在为当前运行生成论文分析")
    generate_initial_analysis(settings, pdf_path)
    run_logger.debug("Bootstrap analysis ready at %s", settings.paper_analysis_path)

    inputs = {
        "messages": [
            {
                "role": "user",
                "content": build_user_prompt(str(pdf_path), str(settings.output_root)),
            }
        ]
    }
    config = {
        "configurable": {"thread_id": run_id},
        "recursion_limit": 60,
    }

    final_state = None
    last_progress = ""
    try:
        for chunk in agent.stream(
            inputs,
            config=config,
            stream_mode=["updates", "messages", "tasks", "values"],
            version="v2",
            subgraphs=True,
        ):
            chunk_type = chunk["type"]
            namespace = chunk.get("ns", ())

            if chunk_type == "messages":
                message_chunk, metadata = chunk["data"]
                if message_chunk.content:
                    run_logger.debug(
                        "STREAM messages ns=%s metadata=%s token=%s",
                        namespace,
                        serialize_for_log(metadata),
                        serialize_for_log(message_chunk.content),
                    )
            elif chunk_type == "values":
                final_state = chunk["data"]
                run_logger.debug("STREAM values ns=%s keys=%s", namespace, list(final_state.keys()))
            elif chunk_type == "tasks":
                task_data = chunk["data"]
                run_logger.debug(
                    "STREAM tasks ns=%s data=%s",
                    namespace,
                    serialize_for_log(task_data),
                )
                task_name = task_data.get("name")
                if task_name:
                    progress = _task_progress(task_name, namespace, task_data)
                    if progress and progress != last_progress:
                        _print_progress(progress)
                        last_progress = progress
            else:
                run_logger.debug(
                    "STREAM %s ns=%s data=%s",
                    chunk_type,
                    namespace,
                    serialize_for_log(chunk["data"]),
                )
    except Exception:
        run_logger.exception("Agent run failed")
        raise

    if final_state is None:
        raise RuntimeError(f"Agent run ended without a final state. Check log file: {log_path}")

    if not settings.paper_analysis_path.exists():
        raise RuntimeError(
            f"Current run did not write required analysis artifact: {settings.paper_analysis_path}. "
            f"Check log file: {log_path}"
        )

    ensure_minimum_generated_project(settings)

    _print_progress("正在生成本轮验证报告")
    generate_verification_report(settings)

    run_logger.debug("Agent run completed with final keys=%s", list(final_state.keys()))
    print(final_state)


if __name__ == "__main__":
    main()
