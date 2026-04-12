"""Environment Configuration Agent for managing dependencies and setup."""

from typing import Dict, Any
import os

from .base import BaseAgent
from ..tools.llm_client import LLMClient
from ..prompts import PROMPTS


class EnvConfigAgent(BaseAgent):
    """Agent for configuring environment and managing dependencies."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize environment configuration agent.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__("EnvConfig", config)
        self.llm_client = LLMClient()

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Configure environment for generated code.

        Args:
            state: Current state containing generated_code

        Returns:
            Updated state with env_config
        """
        generated_code = state.get("generated_code")

        if not generated_code:
            return {
                **state,
                "errors": state.get("errors", []) + ["Generated code not available for env config"],
            }

        code_dir = generated_code.get("code_dir")
        code_files = generated_code.get("files", [])

        try:
            # 读取所有Python代码文件内容
            code_contents = {}
            for file_path in code_files:
                full_path = os.path.join(code_dir, file_path)
                if full_path.endswith('.py') and os.path.exists(full_path):
                    with open(full_path, 'r', encoding='utf-8') as f:
                        code_contents[file_path] = f.read()

            # 使用LLM分析依赖
            code_summary = self._format_code_summary(code_contents)
            prompt = PROMPTS.format_template(
                "env_config",
                code_summary=code_summary
            )

            system_prompt = """You are a Python environment configuration expert. Analyze code dependencies and generate compatible configuration files."""

            env_analysis = self.llm_client.generate_structured(
                prompt=prompt,
                output_format={
                    "dependencies": [{"name": "string", "version": "string", "purpose": "string"}],
                    "requirements_txt": "string",
                    "setup_instructions": "string",
                    "notes": "string"
                },
                system_prompt=system_prompt,
            )

            # 写入requirements.txt
            req_path = os.path.join(code_dir, "requirements.txt")
            with open(req_path, 'w', encoding='utf-8') as f:
                f.write(env_analysis["requirements_txt"])

            env_config = {
                "dependencies": env_analysis["dependencies"],
                "requirements_path": req_path,
                "requirements_content": env_analysis["requirements_txt"],
                "setup_instructions": env_analysis["setup_instructions"],
                "notes": env_analysis.get("notes", "")
            }

            return {
                **state,
                "env_config": env_config,
                "current_step": "env_config_completed",
            }

        except Exception as e:
            return {
                **state,
                "errors": state.get("errors", []) + [f"Environment configuration failed: {str(e)}"],
            }

    def _format_code_summary(self, code_contents: Dict[str, str]) -> str:
        """Format code contents for LLM analysis.

        Args:
            code_contents: Dict mapping file paths to content

        Returns:
            Formatted string summary
        """
        lines = []
        for file_path, content in code_contents.items():
            lines.append(f"\n# File: {file_path}")
            # 只提取import语句
            import_lines = []
            for line in content.split('\n'):
                stripped = line.strip()
                if stripped.startswith('import ') or stripped.startswith('from '):
                    import_lines.append(line)
            if import_lines:
                lines.extend(import_lines)
        return lines.join("\n")
