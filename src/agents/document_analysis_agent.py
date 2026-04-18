"""Document Analysis Agent for reading and analyzing research papers.

This agent combines PDF reading and algorithm analysis capabilities.
"""

from typing import Dict, Any
import os

from .base import BaseAgent
from ..tools.pdf_parser import PDFParser, ParserConfig
from ..tools.llm_client import LLMClient
from ..prompts import PROMPTS


class DocumentAnalysisAgent(BaseAgent):
    """Agent for reading and analyzing research papers.

    This agent handles both PDF parsing and algorithm extraction:
    1. Reads and parses PDF files
    2. Extracts text, structure, metadata
    3. Analyzes paper content to extract algorithm details
    4. Uses LLM to understand algorithm logic, hyperparameters, requirements
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize document analysis agent.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__("DocumentAnalysis", config)

        parser_config = ParserConfig(
            extract_formulas=config.get("extract_formulas", True),
            extract_figures=config.get("extract_figures", True),
        )

        self.parser = PDFParser(parser_config)
        self.llm_client = LLMClient()

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the document and extract algorithm information.

        Args:
            state: Current state containing pdf_path

        Returns:
            Updated state with paper
_content and algorithm_analysis
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

            # Step 1: Parse PDF
            paper_content = self.parser.parse(pdf_path)

            # Step 2: Analyze algorithm
            algorithm_analysis = self._analyze_algorithm(paper_content)

            # Update state
            return {
                **state,
                "paper_content": paper_content,
                "algorithm_analysis": algorithm_analysis,
                "current_step": "document_analysis_completed",
            }

        except FileNotFoundError as e:
            return {
                **state,
                "errors": state.get("errors", []) + [str(e)],
            }
        except Exception as e:
            return {
                **state,
                "errors": state.get("errors", []) + [f"Document analysis failed: {str(e)}"],
            }

    def _analyze_algorithm(self, paper_content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze paper content to extract algorithm information.

        Args:
            paper_content: Dictionary containing paper content

        Returns:
            Dictionary with algorithm analysis
        """
        # Prepare paper text for analysis
        paper_text = paper_content.get("full_text", "")

        if not paper_text:
            raise ValueError("Empty paper text")

        # Limit text length for LLM
        max_length = 150000  # Approximate token limit
        if len(paper_text) > max_length:
            paper_text = paper_text[:max_length] + "..."

        # Format prompt using prompt system
        prompt = PROMPTS.format_template(
            "algorithm_analyzer",
            paper_content=paper_text,
            title=paper_content.get("title", "Unknown"),
            abstract=paper_content.get("abstract", ""),
        )

        # Add system prompt for better results
        system_prompt = """You are an expert in machine learning and algorithm research. You specialize in understanding and extracting algorithm details from research papers. Always provide accurate, well-structured responses in JSON format."""

        # Call LLM to analyze
        algorithm_analysis = self.llm_client.generate_structured(
            prompt=prompt,
            output_format={
                "algorithm_name": "string",
                "algorithm_type": "string",
                "core_logic": "string",
                "pseudocode": "string",
                "hyperparameters": {},
                "requirements": {
                    "dataset": "string",
                    "frameworks": [],
                    "compute": "string",
                },
                "data_flow": "string",
            },
            system_prompt=system_prompt,
        )

        # Validate required fields
        required_fields = [
            "algorithm_name",
            "algorithm_type",
            "core_logic",
            "hyperparameters",
            "requirements",
        ]

        for field in required_fields:
            if field not in algorithm_analysis:
                algorithm_analysis[field] = "Unknown" if field in ["algorithm_name", "algorithm_type", "core_logic"] else {}

        return algorithm_analysis
