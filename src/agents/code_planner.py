"""Code Planner Agent for planning code reproduction."""

from typing import Dict, Any
import os

from .base import BaseAgent
from ..tools.llm_client import LLMClient


class CodePlannerAgent(BaseAgent):
    """Agent for planning how to reproduce the algorithm code."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize code planner agent.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__("CodePlanner", config)
        self.llm_client = LLMClient()
        self.prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        """Load the prompt template from file or use default."""
        prompt_template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "..", "prompts", "planner.txt"
        )

        if os.path.exists(prompt_template_path):
            with open(prompt_template_path, "r", encoding="utf-8") as f:
                return f.read()

        # Default prompt template
        return """You are an expert software architect planning the implementation of a machine learning algorithm based on a research paper.

Algorithm Information:
{algorithm_info}

Based on the algorithm information above, create a comprehensive implementation plan. Consider:

1. Project Structure:
   - Main script for training/inference
   - Data loading module
   - Model definition module
   - Configuration file
   - Utility functions (if needed)
   - Test script

2. Implementation Steps:
   - Break down the implementation into clear, sequential steps
   - Each step should be implementable and testable

3. Dependencies:
   - List all required Python packages with versions
   - Identify any system dependencies

4. Entry Points:
   - Main training script
   - Testing/evaluation script (if applicable)

5. Testing Plan:
   - How to validate the implementation
   - What metrics to use
   - Test data requirements

Provide your response as a structured JSON with these fields:
- project_structure: list of dicts with fields:
  - path: string (relative path)
  - description: string (what this file contains)
  - type: string (script, module, config, etc.)
- implementation_steps: list of strings (sequential steps)
- dependencies: dict with fields:
  - python_packages: list of strings (package==version)
  - system_packages: list of strings
- entry_points: list of strings (main entry point files)
- test_plan: string (testing strategy)
"""

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Plan the code reproduction strategy.

        Args:
            state: Current state containing algorithm_analysis

        Returns:
            Updated state with code_plan
        """
        algorithm_analysis = state.get("algorithm_analysis")

        if not algorithm_analysis:
            return {
                **state,
                "errors": state.get("errors", []) + ["Algorithm analysis not available"],
            }

        try:
            # Prepare algorithm information for the prompt
            algorithm_info = f"""
Algorithm Name: {algorithm_analysis.get('algorithm_name', 'Unknown')}
Algorithm Type: {algorithm_analysis.get('algorithm_type', 'Unknown')}

Core Logic:
{algorithm_analysis.get('core_logic', 'Not available')}

Pseudocode:
{algorithm_analysis.get('pseudocode', 'Not available')}

Hyperparameters: {algorithm_analysis.get('hyperparameters', {})}

Requirements:
- Dataset: {algorithm_analysis.get('requirements', {}).get('dataset', 'Not specified')}
- Frameworks: {algorithm_analysis.get('requirements', {}).get('frameworks', [])}
- Compute: {algorithm_analysis.get('requirements', {}).get('compute', 'Not specified')}

Data Flow:
{algorithm_analysis.get('data_flow', 'Not available')}
"""

            # Create the prompt
            prompt = self.prompt_template.format(algorithm_info=algorithm_info)

            # Add system prompt
            system_prompt = """You are an expert software architect with deep knowledge of machine learning frameworks and best practices. Create detailed, practical implementation plans that are ready to execute. Always respond in valid JSON format."""

            # Call LLM to plan
            code_plan = self.llm_client.generate_structured(
                prompt=prompt,
                output_format={
                    "project_structure": [
                        {
                            "path": "string",
                            "description": "string",
                            "type": "string",
                        }
                    ],
                    "implementation_steps": [],
                    "dependencies": {
                        "python_packages": [],
                        "system_packages": [],
                    },
                    "entry_points": [],
                    "test_plan": "string",
                },
                system_prompt=system_prompt,
            )

            # Validate required fields
            required_fields = [
                "project_structure",
                "implementation_steps",
                "dependencies",
            ]

            for field in required_fields:
                if field not in code_plan:
                    code_plan[field] = [] if field in ["implementation_steps"] else {}

            # Update state
            return {
                **state,
                "code_plan": code_plan,
                "current_step": "code_planning_completed",
            }

        except Exception as e:
            return {
                **state,
                "errors": state.get("errors", []) + [f"Code planning failed: {str(e)}"],
            }
