"""PDF Reader Agent for reading and parsing research papers."""

from typing import Dict, Any
import os

from .base import BaseAgent
from ..tools.pdf_parser import PDFParser, ParserConfig


class PDFReaderAgent(BaseAgent):
    """Agent for reading and parsing PDF files."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize PDF reader agent.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__("PDFReader", config)

        parser_config = ParserConfig(
            extract_formulas=config.get("extract_formulas", True),
            extract_figures=config.get("extract_figures", True),
        )

        self.parser = PDFParser(parser_config)

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Read and parse the PDF file.

        Args:
            state: Current state containing pdf_path

        Returns:
            Updated state with paper_content
        """
        pdf_path = state.get("pdf_path")

        if not pdf_path:
            return {
                **state,
                "errors": state.get("errors", []) + ["PDF path not provided"],
            }

        try:
            # Validate file exists
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")

            # Parse the PDF
            paper_content = self.parser.parse(pdf_path)

            # Update state
            return {
                **state,
                "paper_content": paper_content,
                "current_step": "pdf_reading_completed",
            }

        except FileNotFoundError as e:
            return {
                **state,
                "errors": state.get("errors", []) + [str(e)],
            }
        except Exception as e:
            return {
                **state,
                "errors": state.get("errors", []) + [f"PDF parsing failed: {str(e)}"],
            }
