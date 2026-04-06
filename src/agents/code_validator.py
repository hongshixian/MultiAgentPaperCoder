"""Code Validator Agent for validating generated code."""

from typing import Dict, Any

from .base import BaseAgent
from ..tools.code_executor import CodeExecutor, ExecutorConfig


class CodeValidatorAgent(BaseAgent):
    """Agent for validating and testing generated code."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize code validator agent.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__("CodeValidator", config)

        executor_config = ExecutorConfig(
            conda_env_name=config.get("conda_env_name", "py12pt"),
            timeout=config.get("timeout", 300),
            max_retries=config.get("max_retries", 3),
        )

        self.executor = CodeExecutor(executor_config)

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the generated code.

        Args:
            state: Current state containing generated_code

        Returns:
            Updated state with validation_result
        """
        generated_code = state.get("generated_code")

        if not generated_code:
            return {
                **state,
                "errors": state.get("errors", []) + ["Generated code not available"],
            }

        code_dir = generated_code.get("code_dir")
        entry_points = state.get("code_plan", {}).get("entry_points", [])
        entry_point = entry_points[0] if entry_points else "main.py"

        try:
            # Execute the generated code
            execution_result = self.executor.execute_generated_code(
                code_dir=code_dir,
                entry_point=entry_point,
            )

            # Analyze the result
            if execution_result["success"]:
                validation_result = {
                    "status": "success",
                    "execution_time": execution_result["execution_time"],
                    "output": execution_result["stdout"],
                    "error_log": "",
                    "fix_suggestions": [],
                    "validation_report": f"Code executed successfully in {execution_result['execution_time']:.2f} seconds.",
                }
            else:
                # Code failed - analyze errors
                error_log = execution_result.get("stderr", "") or execution_result.get("error", "")
                fix_suggestions = self._analyze_errors(error_log)

                validation_result = {
                    "status": "failed",
                    "execution_time": execution_result["execution_time"],
                    "output": execution_result.get("stdout", ""),
                    "error_log": error_log,
                    "fix_suggestions": fix_suggestions,
                    "validation_report": f"Code execution failed after {execution_result['execution_time']:.2f} seconds.",
                }

            # Update state
            return {
                **state,
                "validation_result": validation_result,
                "current_step": "validation_completed",
            }

        except Exception as e:
            return {
                **state,
                "errors": state.get("errors", []) + [f"Code validation failed: {str(e)}"],
            }

    def _analyze_errors(self, error_log: str) -> list:
        """Analyze error log and provide fix suggestions.

        Args:
            error_log: Error log from code execution

        Returns:
            List of fix suggestions
        """
        suggestions = []

        error_log_lower = error_log.lower()

        # Check for common errors
        if "modulenotfounderror" in error_log_lower:
            if "torch" in error_log_lower:
                suggestions.append(
                    "Missing PyTorch. Install it with: pip install torch torchvision"
                )
            elif "tensorflow" in error_log_lower:
                suggestions.append(
                    "Missing TensorFlow. Install it with: pip install tensorflow"
                )
            elif "numpy" in error_log_lower:
                suggestions.append(
                    "Missing NumPy. Install it with: pip install numpy"
                )
            else:
                suggestions.append(
                    "Missing dependencies. Check requirements.txt and install with: pip install -r requirements.txt"
                )

        if "syntaxerror" in error_log_lower:
            suggestions.append("Syntax error detected in generated code. Check the generated files for syntax issues.")

        if "indentationerror" in error_log_lower:
            suggestions.append("Indentation error detected. Check code formatting.")

        if "attributeerror" in error_log_lower:
            suggestions.append("Attribute error detected. The code may be using incorrect attributes or methods.")

        if "typeerror" in error_log_lower:
            suggestions.append("Type error detected. Check variable types in the generated code.")

        if "keyerror" in error_log_lower:
            suggestions.append("Key error detected. Check dictionary access in the generated code.")

        if "cuda" in error_log_lower and "not" in error_log_lower:
            suggestions.append("CUDA not available. The code may require GPU support. Install CUDA or run on CPU.")

        if "memory" in error_log_lower and "error" in error_log_lower:
            suggestions.append("Memory error detected. Try reducing batch size or using smaller models.")

        if "file" in error_log_lower and "not" in error_log_lower and "found" in error_log_lower:
            suggestions.append("File not found error. Check file paths and ensure all required files exist.")

        # If no specific suggestions found
        if not suggestions:
            suggestions.append(
                "Unexpected error occurred. Review the error log and consider debugging the generated code manually."
            )

        return suggestions
