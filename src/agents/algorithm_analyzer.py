"""Algorithm Analyzer Agent for understanding paper algorithms."""

from typing import Dict, Any
import os

from .base import BaseAgent
from ..tools.llm_client import LLMClient


class AlgorithmAnalyzerAgent(BaseAgent):
    """Agent for analyzing and extracting algorithm information from papers."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize algorithm analyzer agent.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__("AlgorithmAnalyzer", config)
        self.llm_client = LLMClient()
        self.prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        """Load the prompt template from file or use default."""
        prompt_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "..", "prompts", "analyzer.txt"
        )

        if os.path.exists(prompt_file):
            with open(prompt_file, "r", encoding="utf-8") as f:
                return f.read()

        # Default prompt template
        return """You are an expert algorithm researcher analyzing a research paper. Your task is to extract the key algorithm information from the paper.

Paper Content:
{paper_content}

Please analyze the paper and extract the following information:
1. Algorithm name and type (classification, regression, generation, optimization, etc.)
2. Core logic and main steps of the algorithm
3. Any pseudocode or algorithm descriptions
4. Hyperparameters and their default values
5. Dataset requirements
6. Required frameworks or libraries (PyTorch, TensorFlow, NumPy, etc.)
7. Computational requirements
8. Data flow and architecture

Provide your response as a structured JSON with these fields:
- algorithm_name: string
- algorithm_type: string
- core_logic: string (detailed description)
- pseudocode: string (any pseudocode or algorithm steps)
- hyperparameters: dict (parameter name -> default value)
- requirements: dict with fields:
  - dataset: string
  - frameworks: list of strings
  - compute: string
- data_flow: string (description of data flow)
"""

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the paper and extract algorithm information.

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
            # Prepare the paper text for analysis
            paper_text = paper_content.get("full_text", "")

            if not paper_text:
                raise ValueError("Empty paper text")

            # Limit text length for LLM
            max_length = 150000  # Approximate token limit
            if len(paper_text) > max_length:
                paper_text = paper_text[:max_length] + "..."

            # Create the prompt
            prompt = self.prompt_template.format(
                paper_text=paper_text,
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
