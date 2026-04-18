"""Error Repair Agent for fixing code execution errors."""

from typing import Dict, Any, List
import os

from .base import BaseAgent
from ..llms.llm_client import LLMClient
from ..prompts import PROMPTS


class ErrorRepairAgent(BaseAgent):
    """Agent for analyzing and repairing code errors."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize error repair agent.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__("ErrorRepair", config)
        self.llm_client = LLMClient()

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze errors and repair code.

        Args:
            state: Current state containing generated_code and validation_result

        Returns:
            Updated state with repaired code
        """
        generated_code = state.get("generated_code")
        validation_result = state.get("validation_result")
        repair_history = state.get("repair_history", [])

        if not generated_code or not validation_result:
            return {
                **state,
                "errors": state.get("errors", []) + ["Missing generated code or validation result for error repair"],
            }

        code_dir = generated_code.get("code_dir")

        try:
            # 获取错误信息
            error_log = validation_result.get("error_log", "")
            stderr = validation_result.get("stderr", "")

            full_error = error_log or stderr or "Unknown error"

            # 读取当前代码（可能包含之前的修复）
            current_files = {}
            for file_path in generated_code.get("files", []):
                full_path = os.path.join(code_dir, file_path)
                if os.path.exists(full_path):
                    with open(full_path, 'r', encoding='utf-8') as f:
                        current_files[file_path] = f.read()

            # 使用LLM分析错误并生成修复
            files_summary = self._format_files_summary(current_files)
            repair_history_str = self._format_repair_history(repair_history)
            prompt = PROMPTS.format_template(
                "error_repair",
                error_log=full_error,
                current_files_summary=files_summary,
                repair_history=repair_history_str
            )

            system_prompt = PROMPTS.get_system_prompt("error_repair")

            repair_plan = self.llm_client.generate_structured(
                prompt=prompt,
                output_format={
                    "error_analysis": "string",
                    "root_cause": "string",
                    "fixes": [
                        {"file": "string", "original_snippet": "string", "fixed_snippet": "string", "reason": "string"}
                    ],
                    "additional_dependencies": ["string"]
                },
                system_prompt=system_prompt,
            )

            # 应用修复
            fixed_files = []
            for fix in repair_plan.get("fixes", []):
                file_path = fix.get("file")
                full_path = os.path.join(code_dir, file_path)

                if file_path in current_files:
                    content = current_files[file_path]
                    original_snippet = fix.get("original_snippet", "")
                    fixed_snippet = fix.get("fixed_snippet", "")

                    if original_snippet and original_snippet in content:
                        new_content = content.replace(original_snippet, fixed_snippet, 1)
                        with open(full_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        fixed_files.append(file_path)
                        current_files[file_path] = new_content

            # 处理额外依赖
            additional_deps = repair_plan.get("additional_dependencies", [])
            if additional_deps:
                self._update_requirements(code_dir, additional_deps)

            # 记录修复历史
            repair_entry = {
                "iteration": len(repair_history) + 1,
                "error_analysis": repair_plan.get("error_analysis", ""),
                "root_cause": repair_plan.get("root_cause", ""),
                "files_fixed": fixed_files,
                "additional_dependencies": additional_deps
            }
            repair_history.append(repair_entry)

            # 更新generated_code状态
            updated_generated_code = {
                **generated_code,
                "files": list(current_files.keys()),
                "repair_history": repair_history
            }

            return {
                **state,
                "generated_code": updated_generated_code,
                "repair_history": repair_history,
                "current_step": "error_repair_completed"
            }

        except Exception as e:
            return {
                **state,
                "errors": state.get("errors", []) + [f"Error repair failed: {str(e)}"],
            }

    def _format_files_summary(self, current_files: Dict[str, str]) -> str:
        """Format current files for LLM analysis.

        Args:
            current_files: Dict mapping file paths to content

        Returns:
            Formatted string summary
        """
        lines = []
        for file_path, content in current_files.items():
            lines.append(f"\n# File: {file_path}")
            lines.append(content)
        return "\n".join(lines)

    def _format_repair_history(self, repair_history: List[Dict[str, Any]]) -> str:
        """Format repair history for context.

        Args:
            repair_history: List of previous repair attempts

        Returns:
            Formatted string summary
        """
        if not repair_history:
            return "No previous repair attempts."

        lines = ["Previous repair attempts:"]
        for i, entry in enumerate(repair_history, start=1):
            lines.append(f"\n  Attempt {i}:")
            lines.append(f"    Root cause: {entry.get('root_cause', 'N/A')}")
            lines.append(f"    Files fixed: {entry.get('files_fixed', [])}")
        return "\n".join(lines)

    def _update_requirements(self, code_dir: str, dependencies: List[str]):
        """Update requirements.txt with additional dependencies.

        Args:
            code_dir: Directory containing requirements.txt
            dependencies: List of package names to add
        """
        req_path = os.path.join(code_dir, "requirements.txt")
        existing = set()

        if os.path.exists(req_path):
            with open(req_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Extract package name (before version)
                        pkg = line.split('==')[0].split('>=')[0].split('<=')[0].strip()
                        existing.add(pkg.lower())

        with open(req_path, 'a', encoding='utf-8') as f:
            for dep in dependencies:
                if dep.lower() not in existing:
                    f.write(f"{dep}\n")
