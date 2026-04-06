"""PDF Parser for reading and processing research papers."""

import os
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class ParserEngine(Enum):
    """Available PDF parsing engines."""

    PDFPLUMBER = "pdfplumber"
    PYPDF2 = "PyPDF2"


@dataclass
class ParserConfig:
    """Configuration for PDF parser."""

    engine: ParserEngine = ParserEngine.PDFPLUMBER
    extract_formulas: bool = True
    extract_figures: bool = True
    chunk_size: int = 4000  # Characters per chunk
    overlap: int = 200  # Overlap between chunks


class PDFParser:
    """Parser for reading and extracting content from PDF files."""

    def __init__(self, config: Optional[ParserConfig] = None):
        """Initialize PDF parser.

        Args:
            config: Optional parser configuration
        """
        self.config = config or ParserConfig()
        self._validate_engine()

    def _validate_engine(self):
        """Validate that the selected engine is available."""
        if self.config.engine == ParserEngine.PDFPLUMBER:
            try:
                import pdfplumber
            except ImportError:
                raise ImportError(
                    "pdfplumber not installed. "
                    "Install it with: pip install pdfplumber"
                )
        elif self.config.engine == ParserEngine.PYPDF2:
            try:
                import PyPDF2
            except ImportError:
                raise ImportError(
                    "PyPDF2 not installed. "
                    "Install it with: pip install PyPDF2"
                )

    def parse(self, pdf_path: str) -> Dict[str, Any]:
        """Parse PDF file and extract structured content.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary containing extracted content:
            - full_text: Complete text content
            - title: Paper title
            - abstract: Abstract text
            - sections: List of sections
            - formulas: List of formulas (if enabled)
            - figures: List of figure descriptions (if enabled)
            - chunks: List of text chunks for LLM processing
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        pdf_path = os.path.abspath(pdf_path)

        if self.config.engine == ParserEngine.PDFPLUMBER:
            content = self._parse_with_pdfplumber(pdf_path)
        else:
            content = self._parse_with_pypdf2(pdf_path)

        # Post-processing
        content["full_text"] = self._clean_text(content["full_text"])
        content["title"] = self._extract_title(content["full_text"])
        content["abstract"] = self._extract_abstract(content["full_text"])
        content["sections"] = self._extract_sections(content["full_text"])
        content["chunks"] = self._chunk_text(content["full_text"])

        return content

    def _parse_with_pdfplumber(self, pdf_path: str) -> Dict[str, Any]:
        """Parse PDF using pdfplumber."""
        import pdfplumber

        full_text = []
        formulas = []
        figures = []

        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    full_text.append(text)

                if self.config.extract_formulas:
                    # Try to extract text that looks like formulas
                    page_text = text or ""
                    formulas.extend(self._extract_formulas_from_text(page_text))

                if self.config.extract_figures:
                    # Get images/figures from page
                    for img in page.images:
                        figure_info = {
                            "page": page_num + 1,
                        }
                        # Extract bbox if available
                        if hasattr(img, "bbox") and img.bbox:
                            figure_info["bbox"] = img.bbox
                        # Extract stream_type if available
                        if hasattr(img, "stream_type") and img.stream_type:
                            figure_info["type"] = img.stream_type
                        else:
                            figure_info["type"] = "unknown"
                        figures.append(figure_info)

        return {
            "full_text": "\n".join(full_text),
            "formulas": formulas,
            "figures": figures,
        }

    def _parse_with_pypdf2(self, pdf_path: str) -> Dict[str, Any]:
        """Parse PDF using PyPDF2."""
        import PyPDF2

        full_text = []
        formulas = []

        with open(pdf_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    full_text.append(text)
                    if self.config.extract_formulas:
                        formulas.extend(self._extract_formulas_from_text(text))

        return {
            "full_text": "\n".join(full_text),
            "formulas": formulas,
            "figures": [],
        }

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove non-printable characters except newlines
        text = re.sub(r'[^\x20-\x7E\n]', '', text)
        return text.strip()

    def _extract_title(self, text: str) -> str:
        """Extract paper title from text."""
        # Title is usually at the beginning and in all caps or follows specific patterns
        lines = text.split('\n')
        if not lines:
            return "Unknown Title"

        # Try first non-empty line that looks like a title
        for i, line in enumerate(lines[:10]):
            line = line.strip()
            if line and len(line) > 10 and len(line) < 200:
                # Skip lines that are likely metadata
                if not any(x in line.lower() for x in ["university", "institute", "arxiv"]):
                    return line

        return "Unknown Title"

    def _extract_abstract(self, text: str) -> str:
        """Extract abstract from text."""
        abstract_pattern = re.compile(
            r'(?i)abstract\s*:?\s*(.*?)(?=\n\s*(?:introduction|keywords|\d+\.)|$)',
            re.DOTALL
        )
        match = abstract_pattern.search(text)
        if match:
            abstract = match.group(1).strip()
            # Clean up abstract
            abstract = re.sub(r'\s+', ' ', abstract)
            return abstract[:500]  # Limit length
        return ""

    def _extract_sections(self, text: str) -> List[Dict[str, Any]]:
        """Extract section headings from text."""
        section_pattern = re.compile(
            r'(?m)^(?:\d+\.?\s+)?([A-Z][A-Za-z\s]+?)\s*(?:\n|$)(?=\s*\w)',
        )

        sections = []
        lines = text.split('\n')

        for line_num, line in enumerate(lines):
            if section_pattern.match(line.strip()):
                sections.append({
                    "title": line.strip(),
                    "line_number": line_num,
                })

        return sections

    def _extract_formulas_from_text(self, text: str) -> List[str]:
        """Extract formulas from text using heuristics."""
        formulas = []
        # Look for mathematical patterns
        formula_patterns = [
            r'\$.*?\$',  # LaTeX inline math
            r'\\\[.*?\\\]',  # LaTeX display math
            r'\\begin\{equation\}.*?\\end\{equation\}',  # LaTeX equations
        ]

        for pattern in formula_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            formulas.extend(matches)

        return formulas

    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks for LLM processing.

        Args:
            text: Text to chunk

        Returns:
            List of text chunks
        """
        if len(text) <= self.config.chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + self.config.chunk_size

            if end < len(text):
                # Try to find a good break point (sentence boundary)
                for break_char in ['.\n', '.\n\n', '\n\n']:
                    last_break = text.rfind(break_char, start, end)
                    if last_break > start:
                        end = last_break + len(break_char)
                        break
                else:
                    # Fallback to space
                    last_space = text.rfind(' ', start, end)
                    if last_space > start:
                        end = last_space + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - self.config.overlap if end > self.config.overlap else end

        return chunks
