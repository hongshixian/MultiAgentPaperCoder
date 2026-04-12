"""Code Planner Agent for planning code reproduction."""

from typing import Dict, Any

from .base import BaseAgent
from ..tools.llm_client import LLMClient
from ..prompts import PROMPTS


class CodePlannerAgent(BaseAgent):
    """Agent for planning how to reproduce the algorithm code."""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("CodePlanner", config)
        self.llm_client = LLMClient()

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        algorithm_analysis = state.get("algorithm_analysis")

        if not algorithm_analysis:
            return {
                **state,
                "errors": state.get("errors", []) + ["Algorithm analysis not available"],
            }

        try:
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
            prompt = PROMPTS.format_template(
                "code_planner",
                algorithm_info=algorithm_info,
            )

            system_prompt = """You are an expert software architect with deep knowledge of machine learning frameworks and best practices. Create detailed, practical implementation plans that are ready to execute. Always respond in valid JSON format."""

            code_plan = self.llm_client.generate_structured(
                prompt=prompt,
                output_format={
                    "project_structure": [
                        {"path": "string", "description": "string", "type": "string"}
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

            for field in ["project_structure", "implementation_steps", "dependencies"]:
                if field not in code_plan:
                    code_plan[field] = [] if field != "dependencies" else {}

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
