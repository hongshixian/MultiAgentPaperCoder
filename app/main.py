"""CLI entrypoint for the DeepAgents paper reproduction app."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from app.agent import build_agent
from app.config import Settings
from app.logging_utils import create_run_logger, serialize_for_log


def build_user_prompt(pdf_path: str, output_dir: str) -> str:
    """Build the high-level paper reproduction task prompt."""
    return f"""
Run one paper reproduction workflow with these requirements:

1. Read the PDF at this absolute path: {pdf_path}
2. You must use the document-analyst subagent first.
3. The document-analyst subagent must read the paper only through the read_pdf_text tool.
4. Save the analysis under this absolute directory: {output_dir}/artifacts/
5. Use the code-generator subagent to create a minimal Python project under this absolute directory: {output_dir}/generated_code/
4. The generated project must include at least:
   - main.py
   - requirements.txt
6. Use the code-verifier subagent to verify the generated project
7. If verification fails, use the error-repairer subagent and then verify again
8. Do not use generic filesystem tools to inspect the input PDF.
9. Final response must include:
   - paper method summary
   - generated files
   - verification status
   - unresolved issues and risks
"""


def main() -> None:
    """Parse CLI args and invoke the DeepAgents workflow."""
    parser = argparse.ArgumentParser(description="DeepAgents-based paper reproduction tool")
    parser.add_argument("--pdf", required=True, help="Path to the paper PDF")
    parser.add_argument("--output-dir", default="./output", help="Output directory root")
    args = parser.parse_args()

    pdf_path = Path(args.pdf).resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    settings = Settings(output_root=Path(args.output_dir).resolve())
    agent = build_agent(settings)
    run_logger, file_handler, log_path, run_id = create_run_logger(settings.log_dir)
    for name in ["papercoder.tools", "papercoder.tools.pdf", "papercoder.tools.artifacts", "papercoder.tools.exec"]:
        tool_logger = logging.getLogger(name)
        tool_logger.setLevel(logging.INFO)
        tool_logger.handlers.clear()
        tool_logger.addHandler(file_handler)
        tool_logger.propagate = False
    logging.getLogger().setLevel(logging.WARNING)

    run_logger.info("Starting agent run %s", run_id)
    run_logger.info("Resolved PDF path: %s", pdf_path)
    run_logger.info("Resolved output root: %s", settings.output_root)
    run_logger.info("Log file: %s", log_path)
    print(f"Logging agent execution to {log_path}")

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
                    run_logger.info(
                        "STREAM messages ns=%s metadata=%s token=%s",
                        namespace,
                        serialize_for_log(metadata),
                        serialize_for_log(message_chunk.content),
                    )
            elif chunk_type == "values":
                final_state = chunk["data"]
                run_logger.info("STREAM values ns=%s keys=%s", namespace, list(final_state.keys()))
            else:
                run_logger.info(
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

    run_logger.info("Agent run completed with final keys=%s", list(final_state.keys()))
    print(final_state)


if __name__ == "__main__":
    main()
