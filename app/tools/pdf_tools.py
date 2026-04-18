"""PDF tools for paper reproduction."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("papercoder.tools.pdf")


def read_pdf_text(pdf_path: str) -> str:
    """Read PDF text and return a truncated body for agent consumption."""
    try:
        from PyPDF2 import PdfReader
    except ImportError as exc:
        raise ImportError(
            "PyPDF2 is not installed. Install project requirements before reading PDFs."
        ) from exc

    path = Path(pdf_path)
    if not path.exists():
        logger.error("PDF path does not exist: %s", pdf_path)
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    logger.info("Reading PDF text from %s", path)
    reader = PdfReader(str(path))
    chunks: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            chunks.append(text)

    full_text = "\n\n".join(chunks)
    if not full_text:
        logger.error("PDF text extraction returned empty content for %s", path)
        raise ValueError("PDF text extraction returned empty content")

    logger.info("Extracted %d characters from PDF %s", len(full_text), path)
    return full_text[:50000]
