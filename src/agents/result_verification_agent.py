"""Result Verification Agent for comparing results with paper."""

from typing import Dict, Any

from .base import BaseAgent
from ..tools.llm_client import LLMClient
from ..prompts import PROMPTS


class ResultVerificationAgent(BaseAgent):
    """Agent for verifying reproduction results against paper."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize result verification agent.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__("ResultVerification", config)
        self.llm_client = LLMClient()

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Verify reproduction results against paper-reported results.

        Args:
            state: Current state containing validation_result and algorithm_analysis

        Returns:
            Updated state with verification_result
        """
        algorithm_analysis = state.get("algorithm_analysis")
        validation_result = state.get("validation_result")

        if not validation_result:
            return {
                **state,
                "errors": state.get("errors", []) + ["Validation result not available for verification"],
            }

        if validation_result.get("status") != "success":
            # 代码执行失败，不需要结果验证，直接标记需要修复
            return {
                **state,
                "verification_result": {
                    "status": "skipped",
                    "reason": "Code execution failed",
                    "needs_regeneration": False,
                    "needs_repair": True,
                    "quality_score": 0,
                    "assessment": "Cannot verify results - code failed to execute"
                },
                "current_step": "verification_completed"
            }

        try:
            # 准备数据
            code_output = validation_result.get("output", "")
            paper_results = self._extract_paper_results(algorithm_analysis)

            # 使用LLM进行结果对比分析
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

            # 添加额外上下文
            verification["paper_results"] = paper_results
            verification["code_output"] = code_output
            verification["status"] = "completed"

            return {
                **state,
                "verification_result": verification,
                "current_step": "verification_completed"
            }

        except Exception as e:
            return {
                **state,
                "errors": state.get("errors", []) + [f"Result verification failed: {str(e)}"],
            }

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
