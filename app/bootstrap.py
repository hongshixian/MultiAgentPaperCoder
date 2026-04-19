"""Deterministic bootstrap helpers for each paper reproduction run."""

from __future__ import annotations

import logging
from pathlib import Path

from app.config import Settings
from app.tools.artifact_tools import list_files, read_text_file
from app.tools.exec_tools import check_entrypoint_exists, python_syntax_check, run_python_entrypoint
from app.tools.pdf_tools import read_pdf_text

logger = logging.getLogger("papercoder.bootstrap")

BOOTSTRAP_SYSTEM_PROMPT = """
You are preparing a concise implementation-oriented paper analysis for a code generation workflow.

Requirements:
- summarize only what is supported by the provided paper text
- keep the analysis under 1200 words
- focus on method structure, required modules, training flow, evaluation flow, dependencies, and reproduction risks
- mark uncertainty explicitly when the paper leaves details unspecified
- write for an engineer who needs to build a minimal runnable reproduction
"""


def generate_initial_analysis(settings: Settings, pdf_path: Path) -> Path:
    """Create a fresh paper analysis artifact for the current run."""
    paper_text = read_pdf_text(str(pdf_path))
    llm = settings.build_llm()
    response = llm.invoke(
        [
            ("system", BOOTSTRAP_SYSTEM_PROMPT),
            (
                "user",
                (
                    f"Paper path: {pdf_path}\n"
                    f"Write the analysis for this exact output file: {settings.paper_analysis_path}\n\n"
                    f"Paper text:\n{paper_text}"
                ),
            ),
        ]
    )

    analysis = getattr(response, "content", "") or ""
    if isinstance(analysis, list):
        analysis = "\n".join(str(item) for item in analysis)
    analysis = str(analysis).strip()
    if not analysis:
        raise RuntimeError("Bootstrap paper analysis returned empty content")

    settings.paper_analysis_path.parent.mkdir(parents=True, exist_ok=True)
    settings.paper_analysis_path.write_text(analysis, encoding="utf-8")
    logger.info("Saved bootstrap paper analysis to %s (%d chars)", settings.paper_analysis_path, len(analysis))
    return settings.paper_analysis_path


def generate_verification_report(settings: Settings) -> Path:
    """Create a deterministic two-layer verification report for the current run output."""
    files_listing = list_files(str(settings.generated_code_dir))
    requirements_path = settings.generated_code_dir / "requirements.txt"
    requirements_text = ""
    if requirements_path.exists():
        requirements_text = read_text_file(str(requirements_path))

    entrypoint_status = check_entrypoint_exists(str(settings.generated_code_dir))
    syntax_status = python_syntax_check(str(settings.generated_code_dir))
    runtime_status = run_python_entrypoint(str(settings.generated_code_dir))

    has_main = (settings.generated_code_dir / "main.py").exists()
    has_requirements = requirements_path.exists()
    syntax_ok = syntax_status.startswith("PASSED")
    entrypoint_ok = entrypoint_status.startswith("FOUND")
    runtime_ok = runtime_status.startswith("PASSED")
    outcome = "PASS" if has_main and has_requirements and syntax_ok and entrypoint_ok and runtime_ok else "NEEDS_REPAIR"

    report = f"""# Verification Report

Project path: {settings.generated_code_dir}
Report path: {settings.verification_report_path}

## Required Files
- main.py: {"present" if has_main else "missing"}
- requirements.txt: {"present" if has_requirements else "missing"}

## Files Listing
{files_listing or "(no files found)"}

## Layer 1: Deterministic Static Verification

### Entrypoint Check
{entrypoint_status}

### Syntax Check
{syntax_status}

### Requirements Analysis
{requirements_text or "(requirements.txt missing or empty)"}

## Layer 2: Runtime Execution Verification
{runtime_status}

## Functional Assessment
- Layer 1 verifies file presence, entrypoint existence, and Python syntax deterministically.
- Layer 2 runs `python main.py` inside the generated project directory and records stdout/stderr verbatim.

## Risk Assessment
- Runtime verification uses the current local Python environment and does not create an isolated virtualenv.
- Passing runtime execution still does not prove full paper-level correctness.

## Overall Outcome
{outcome}
"""
    settings.verification_report_path.parent.mkdir(parents=True, exist_ok=True)
    settings.verification_report_path.write_text(report, encoding="utf-8")
    logger.info("Saved deterministic verification report to %s", settings.verification_report_path)
    return settings.verification_report_path
