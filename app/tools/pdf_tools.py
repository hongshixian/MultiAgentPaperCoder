"""PDF tools for paper reproduction."""

from __future__ import annotations

from pathlib import Path


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
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    reader = PdfReader(str(path))
    chunks: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            chunks.append(text)

    full_text = "\n\n".join(chunks)
    if not full_text:
        raise ValueError("PDF text extraction returned empty content")

    return full_text[:50000]
