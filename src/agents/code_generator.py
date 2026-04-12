"""Code Generator Agent for generating implementation code."""

from typing import Dict, Any
import os

from .base import BaseAgent
from ..tools.llm_client import LLMClient
from ..prompts import PROMPTS


class CodeGeneratorAgent(BaseAgent):
    """Agent for generating Python code from implementation plan."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize code generator agent.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__("CodeGenerator", config)
        self.llm_client = LLMClient()
        self.output_dir = config.get("output_dir", "./output/generated_code")

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code from the plan.

        Args:
            state: Current state containing algorithm_analysis and code_plan

        Returns:
            Updated state with generated_code
        """
        algorithm_analysis = state.get("algorithm_analysis")
        code_plan = state.get("code_plan")

        if not algorithm_analysis or not code_plan:
            return {
                **state,
                "errors": state.get("errors", []) + ["Missing algorithm analysis or code plan"],
            }

        try:
            # Prepare information for prompt
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

            # Format prompt using new prompt system
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

            # Update state
            return {
                **state,
                "generated_code": generated_code,
                "current_step": "code_generation_completed",
            }

        except Exception as e:
            return {
                **state,
                "errors": state.get("errors", []) + [f"Code generation failed: {str(e)}"],
            }

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
