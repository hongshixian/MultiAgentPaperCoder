"""CLI entry point for the hybrid paper reproduction system.

Usage:
    python -m src.hybrid.main --pdf path/to/paper.pdf [--output-dir ./output]
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .config import Settings
from .logging_utils import create_run_logger
from .state import PaperState
from .workflow import create_workflow


def _print_summary(state: dict) -> None:
    """Print a concise summary of the final workflow state."""
    print("\n" + "=" * 60)
    print("MultiAgentPaperCoder - 执行摘要")
    print("=" * 60)

    # Document analysis
    analysis_status = state.get("analysis_status", "unknown")
    analysis_path = state.get("analysis_path", "")
    print(f"\n文档分析: {analysis_status}")
    if analysis_path:
        print(f"  产物: {analysis_path}")

    # Code generation
    gen_status = state.get("generation_status", "unknown")
    code_dir = state.get("code_dir", "")
    file_list = state.get("file_list", [])
    print(f"\n代码生成: {gen_status}")
    if code_dir:
        print(f"  目录: {code_dir}")
    if file_list:
        print(f"  文件: {', '.join(file_list)}")

    # Code verification
    passed = state.get("verification_passed")
    error_type = state.get("error_type", "")
    error_cause = state.get("error_cause", "")
    error_location = state.get("error_location", "")
    iteration = state.get("iteration_count", 0)
    print(f"\n代码验证: {'通过' if passed else '未通过'}")
    if not passed and error_cause:
        print(f"  错误类型: {error_type}")
        print(f"  错误原因: {error_cause}")
        if error_location and error_location != "unknown":
            print(f"  错误位置: {error_location}")
    if iteration > 0:
        print(f"  修复迭代: {iteration} 次")

    # Errors
    errors = state.get("errors", [])
    if errors:
        print(f"\n错误记录 ({len(errors)} 条):")
        for err in errors[-5:]:
            print(f"  - {err}")

    print("\n" + "=" * 60)


def main() -> None:
    """Parse CLI args and invoke the hybrid workflow."""
    parser = argparse.ArgumentParser(
        description="Hybrid paper reproduction tool (deterministic routing + deepagents sub-agents)"
    )
    parser.add_argument("--pdf", required=True, help="Path to the paper PDF")
    parser.add_argument("--output-dir", default="./output", help="Output directory root")
    parser.add_argument("--max-iterations", type=int, default=5, help="Max repair loop iterations")
    args = parser.parse_args()

    pdf_path = Path(args.pdf).resolve()
    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    # Setup output directory
    base_output_root = Path(args.output_dir).resolve()
    base_settings = Settings(output_root=base_output_root)
    run_output_root = base_settings.create_run_output_root(pdf_path)
    settings = Settings(output_root=run_output_root, log_dir_override=str(base_output_root / "logs"))
    settings.ensure_dirs()

    import os
    os.environ["OUTPUT_ROOT"] = str(settings.output_root)

    # Setup logging
    run_logger, _, log_path, run_id = create_run_logger(settings.log_dir)
    run_logger.info("Starting hybrid workflow run %s", run_id)
    run_logger.info("PDF: %s", pdf_path)
    run_logger.info("Output: %s", settings.output_root)

    print(f"日志文件: {log_path}")
    print(f"输出目录: {settings.output_root}")

    # Build and run workflow
    workflow = create_workflow(settings)

    initial_state: PaperState = {
        "pdf_path": str(pdf_path),
        "iteration_count": 0,
        "max_iterations": args.max_iterations,
        "errors": [],
    }

    try:
        final_state = workflow.invoke(
            initial_state,
            config={"configurable": {"thread_id": run_id}},
        )
    except KeyboardInterrupt:
        print("\n用户中断")
        sys.exit(130)
    except Exception as exc:
        run_logger.exception("Workflow failed")
        print(f"\n执行失败: {exc}", file=sys.stderr)
        sys.exit(1)

    _print_summary(final_state)
    run_logger.info("Workflow completed")

    # Exit code
    if final_state.get("verification_passed"):
        print("\n论文代码复现成功!")
        sys.exit(0)
    else:
        print("\n论文代码复现未完全通过验证。")
        sys.exit(1)


if __name__ == "__main__":
    main()
