"""Algorithm Analyzer Agent for understanding paper algorithms."""

from typing import Dict, Any

from .base import BaseAgent
from ..tools.llm_client import LLMClient
from ..prompts import PROMPTS


class AlgorithmAnalyzerAgent(BaseAgent):
    """Agent for analyzing and extracting algorithm information from papers."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize algorithm analyzer agent.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__("AlgorithmAnalyzer", config)
        self.llm_client = LLMClient()

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze of paper and extract algorithm information.

        Args:
            state: Current state containing paper_content

        Returns:
            Updated state with algorithm_analysis
        """
        paper_content = state.get("paper_content")

        if not paper_content:
            return {
                **state,
                "errors": state.get("errors", []) + ["Paper content not available"],
            }

        try:
            # Prepare of paper text for analysis
            paper_text = paper_content.get("full_text", "")

            if not paper_text:
                raise ValueError("Empty paper text")

            # Limit text length for LLM
            max_length = 150000  # Approximate token limit
            if len(paper_text) > max_length:
                paper_text = paper_text[:max_length] + "..."

            # Format prompt using new prompt system
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

            # Update state
            return {
                **state,
                "algorithm_analysis": algorithm_analysis,
                "current_step": "algorithm_analysis_completed",
            }

        except Exception as e:
            return {
                **state,
                "errors": state.get("errors", []) + [f"Algorithm analysis failed: {str(e)}"],
            }
