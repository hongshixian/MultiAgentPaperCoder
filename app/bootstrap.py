"""Deterministic bootstrap helpers for each paper reproduction run."""

from __future__ import annotations

import logging
from pathlib import Path

from app.config import Settings
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
