"""Code Verification Agent for validating and verifying generated code.

This agent combines code validation and result verification capabilities.
"""

from typing import Dict, Any

from .base import BaseAgent
from ..tools.code_executor import CodeExecutor, ExecutorConfig
from ..tools.llm_client import LLMClient
from ..prompts import PROMPTS


class CodeVerificationAgent(BaseAgent):
    """Agent for validating and verifying generated code.

    This agent handles both code execution validation and result quality assessment:
    1. Executes generated code in isolated conda environment
    2. Monitors execution, captures errors, provides fix suggestions
    3. Verifies execution results meet expected outcomes
    4. Assesses quality of generated code execution
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize code verification agent.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__("CodeVerification", config)

        executor_config = ExecutorConfig(
            conda_env_name=config.get("conda_env_name", "py12pt"),
            timeout=config.get("timeout", 300),
            max_retries=config.get("max_retries", 3),
        )

        self.executor = CodeExecutor(executor_config)
        self.llm_client = LLMClient()

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and verify generated code.

        Args:
            state: Current state containing generated_code and algorithm_analysis

        Returns:
            Updated state with validation_result and verification_result
        """
        algorithm_analysis = state.get("algorithm_analysis")
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
            # Step 1: Validate code execution
            validation_result = self._validate_code(code_dir, entry_point)

            # Step 2: Verify results
            verification_result = self._verify_results(
                algorithm_analysis,
                validation_result
            )

            # Update state
            return {
                **state,
                "validation_result": validation_result,
                "verification_result": verification_result,
                "current_step": "code_verification_completed",
            }

        except Exception as e:
            return {
                **state,
                "errors": state.get("errors", []) + [f"Code verification failed: {str(e)}"],
            }

    def _validate_code(self, code_dir: str, entry_point: str) -> Dict[str, Any]:
        """Validate code by executing it.

        Args:
            code_dir: Directory containing generated code
            entry_point: Entry point script name

        Returns:
            Dictionary with validation result
        """
        # Execute generated code
        execution_result = self.executor.execute_generated_code(
            code_dir=code_dir,
            entry_point=entry_point,
        )

        # Analyze result
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

        return validation_result

    def _verify_results(
        self,
        algorithm_analysis: Dict[str, Any],
        validation_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Verify reproduction results against paper-reported results.

        Args:
            algorithm_analysis: Algorithm analysis from paper
            validation_result: Result from code validation

        Returns:
            Dictionary with verification result
        """
        if validation_result.get("status") != "success":
            # Code execution failed, skip result verification
            return {
                "status": "skipped",
                "reason": "Code execution failed",
                "needs_regeneration": False,
                "needs_repair": True,
                "quality_score": 0,
                "assessment": "Cannot verify results - code failed to execute"
            }

        try:
            # Prepare data
            code_output = validation_result.get("output", "")
            paper_results = self._extract_paper_results(algorithm_analysis)

            # Use LLM for result comparison
            prompt = PROMPTS.format_template(
                "result_verification",
                paper_results=paper_results,
                code_output=code_output
            )

            system_prompt = """You are an academic research evaluation expert. Compare experimental results and assess reproduction quality."""

            verification = self.llm_client.generate_structured(
                prompt=prompt,
                output_format={
                    "metrics_comparison": [
                        {"metric": "string", "paper_value": "string", "code_value": "string", "difference_percent": "string"}
                    ],
                    "quality_score": "number",  # 0-100
                    "assessment": "string",
                    "needs_regeneration": "boolean",
                    "needs_repair": "boolean",
                    "suggestions": ["string"]
                },
                system_prompt=system_prompt,
            )

            # Add additional context
            verification["paper_results"] = paper_results
            verification["code_output"] = code_output
            verification["status"] = "completed"

            return verification

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "quality_score": 0,
                "assessment": f"Result verification failed: {str(e)}",
                "needs_regeneration": False,
                "needs_repair": True,
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
            suggestions.append("Syntax error detected in generated code. Check generated files for syntax issues.")

        if "indentationerror" in error_log_lower:
            suggestions.append("Indentation error detected. Check code formatting.")

        if "attributeerror" in error_log_lower:
            suggestions.append("Attribute error detected. The code may be using incorrect attributes or methods.")

        if "typeerror" in error_log_lower:
            suggestions.append("Type error detected. Check variable types in generated code.")

        if "keyerror" in error_log_lower:
            suggestions.append("Key error detected. Check dictionary access in generated code.")

        if "cuda" in error_log_lower and "not" in error_log_lower:
            suggestions.append("CUDA not available. The code may require GPU support. Install CUDA or run on CPU.")

        if "memory" in error_log_lower and "error" in error_log_lower:
            suggestions.append("Memory error detected. Try reducing batch size or using smaller models.")

        if "file" in error_log_lower and "not" in error_log_lower and "found" in error_log_lower:
            suggestions.append("File not found error. Check file paths and ensure all required files exist.")

        # If no specific suggestions found
        if not suggestions:
            suggestions.append(
                "Unexpected error occurred. Review the error log and consider debugging generated code manually."
            )

        return suggestions

    def _extract_paper_results(self, algorithm_analysis: Dict[str, Any]) -> str:
        """Extract paper-reported results from algorithm analysis.

        Args:
            algorithm_analysis: Algorithm analysis from paper

        Returns:
            Formatted string of paper results
        """
        # Extract any result-related information
        lines = []
        lines.append(f"Algorithm: {algorithm_analysis.get('algorithm_name', 'Unknown')}")
        lines.append(f"Type: {algorithm_analysis.get('algorithm_type', 'Unknown')}")

        # Add any hyperparameters as reference
        hyperparams = algorithm_analysis.get('hyperparameters', {})
        if hyperparams:
            lines.append("\nReported Hyperparameters:")
            for key, value in hyperparams.items():
                lines.append(f"  - {key}: {value}")

        # Add requirements data (may include dataset info)
        requirements = algorithm_analysis.get('requirements', {})
        if requirements:
            lines.append("\nDataset/Requirements:")
            for key, value in requirements.items():
                lines.append(f"  - {key}: {value}")

        # Add any notes about expected results
        lines.append("\nNote: Extract specific experimental results (metrics, accuracy, loss, etc.) from paper text if available.")

        return "\n".join(lines)
