"""Code Generation Agent for planning and generating reproduction code.

This agent combines code planning and generation capabilities.
"""

from typing import Dict, Any
import os

from .base import BaseAgent
from ..llms.llm_client import LLMClient
from ..prompts import PROMPTS


class CodeGenerationAgent(BaseAgent):
    """Agent for planning and generating code from algorithm analysis.

    This agent handles both code planning and generation:
    1. Designs project structure based on algorithm analysis
    2. Plans file organization, implementation steps, dependencies
    3. Generates complete Python code files
    4. Analyzes code dependencies and generates requirements.txt
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize code generation agent.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__("CodeGeneration", config)
        self.llm_client = LLMClient()
        self.output_dir = config.get("output_dir", "./output/generated_code")

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Plan and generate code from algorithm analysis.

        Args:
            state: Current state containing algorithm_analysis

        Returns:
            Updated state with code_plan and generated_code
        """
        algorithm_analysis = state.get("algorithm_analysis")

        if not algorithm_analysis:
            return {
                **state,
                "errors": state.get("errors", []) + ["Algorithm analysis not available"],
            }

        try:
            # Step 1: Generate code plan
            code_plan = self._plan_code(algorithm_analysis)

            # Step 2: Generate code
            generated_code = self._generate_code(algorithm_analysis, code_plan)

            # Update state
            return {
                **state,
                "code_plan": code_plan,
                "generated_code": generated_code,
                "current_step": "code_generation_completed",
            }

        except Exception as e:
            return {
                **state,
                "errors": state.get("errors", []) + [f"Code generation failed: {str(e)}"],
            }

    def _plan_code(self, algorithm_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Plan code implementation based on algorithm analysis.

        Args:
            algorithm_analysis: Dictionary containing algorithm information

        Returns:
            Dictionary with code plan
        """
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

        # Validate required fields
        for field in ["project_structure", "implementation_steps", "dependencies"]:
            if field not in code_plan:
                code_plan[field] = [] if field != "dependencies" else {}

        return code_plan

    def _generate_code(self, algorithm_analysis: Dict[str, Any], code_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code from algorithm analysis and code plan.

        Args:
            algorithm_analysis: Dictionary containing algorithm information
            code_plan: Dictionary containing code plan

        Returns:
            Dictionary with generated code metadata
        """
        algorithm_info = f"""
Algorithm Name: {algorithm_analysis.get('algorithm_name', 'Unknown')}
Algorithm Type: {algorithm_analysis.get('algorithm_type', 'Unknown')}

Core Logic:
{algorithm_analysis.get('core_logic', 'Not available')}

Hyperparameters: {algorithm_analysis.get('hyperparameters', {})}
"""

        code_plan_str = f"""
Project Structure:
{self._format_project_structure(code_plan.get('project_structure', []))}

Implementation Steps:
{self._format_implementation_steps(code_plan.get('implementation_steps', []))}

Dependencies:
- Python: {', '.join(code_plan.get('dependencies', {}).get('python_packages', []))}
- System: {', '.join(code_plan.get('dependencies', {}).get('system_packages', []))}

Entry Points: {', '.join(code_plan.get('entry_points', []))}
"""

        # Format prompt using prompt system
        prompt = PROMPTS.format_template(
            "code_generator",
            algorithm_info=algorithm_info,
            code_plan=code_plan_str,
        )

        # Add system prompt
        system_prompt = """You are an expert Python developer. Generate clean, production-ready code that follows best practices. Include proper error handling, logging, and documentation. Always respond in valid JSON format."""

        # Call LLM to generate code
        generated_data = self.llm_client.generate_structured(
            prompt=prompt,
            output_format={
                "files": [
                    {
                        "path": "string",
                        "content": "string",
                    }
                ],
                "requirements_txt": "string",
                "summary": "string",
            },
            system_prompt=system_prompt,
        )

        # Write files to disk
        file_paths = []
        written_files = []

        for file_info in generated_data.get("files", []):
            file_path = os.path.join(self.output_dir, file_info["path"])
            file_content = file_info.get("content", "")

            # Create directory if needed
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Write file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(file_content)

            file_paths.append(file_path)
            written_files.append(file_info["path"])

        # Write requirements.txt if provided
        if generated_data.get("requirements_txt"):
            req_path = os.path.join(self.output_dir, "requirements.txt")
            with open(req_path, "w", encoding="utf-8") as f:
                f.write(generated_data["requirements_txt"])
            file_paths.append(req_path)

        generated_code = {
            "files": written_files,
            "file_paths": file_paths,
            "code_dir": self.output_dir,
            "summary": generated_data.get("summary", ""),
            "total_files": len(file_paths),
        }

        return generated_code

    def _format_project_structure(self, structure: list) -> str:
        """Format project structure for prompt."""
        lines = []
        for item in structure:
            lines.append(f"  - {item.get('path', '')}: {item.get('description', '')}")
        return "\n".join(lines)

    def _format_implementation_steps(self, steps: list) -> str:
        """Format implementation steps for prompt."""
        lines = []
        for i, step in enumerate(steps, 1):
            lines.append(f"  {i}. {step}")
        return "\n".join(lines)
