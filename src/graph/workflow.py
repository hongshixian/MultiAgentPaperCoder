"""Workflow orchestration using LangGraph."""

from typing import Dict, Any, Literal
import os
from dotenv import load_dotenv

load_dotenv()


class PaperCoderWorkflow:
    """Orchestrates the paper coding workflow using agents sequentially."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the workflow.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}

        # Import agents here to avoid circular imports
        from ..agents.pdf_reader import PDFReaderAgent
        from ..agents.algorithm_analyzer import AlgorithmAnalyzerAgent
        from ..agents.code_planner import CodePlannerAgent
        from ..agents.code_generator import CodeGeneratorAgent
        from ..agents.code_validator import CodeValidatorAgent

        # Initialize agents
        self.pdf_reader = PDFReaderAgent(self.config)
        self.algorithm_analyzer = AlgorithmAnalyzerAgent(self.config)
        self.code_planner = CodePlannerAgent(self.config)
        self.code_generator = CodeGeneratorAgent({
            **self.config,
            "output_dir": self.config.get("output_dir", "./output/generated_code"),
        })
        self.code_validator = CodeValidatorAgent({
            **self.config,
            "conda_env_name": self.config.get("conda_env_name", "py12pt"),
        })

    def _create_initial_state(self, pdf_path: str) -> Dict[str, Any]:
        """Create initial state for the workflow.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Initial state dictionary
        """
        return {
            "pdf_path": pdf_path,
            "paper_content": None,
            "algorithm_analysis": None,
            "code_plan": None,
            "generated_code": None,
            "validation_result": None,
            "current_step": "start",
            "errors": [],
            "retry_count": 0,
            "max_retries": self.config.get("max_retries", 3),
        }

    def _should_continue(self, state: Dict[str, Any]) -> bool:
        """Check if workflow should continue.

        Args:
            state: Current state

        Returns:
            True if workflow should continue, False otherwise
        """
        # Stop if there are critical errors
        errors = state.get("errors", [])
        if errors:
            # Check if any errors are critical (not retryable)
            critical_errors = [
                "PDF file not found",
                "Paper content not available",
                "Algorithm analysis not available",
                "Missing algorithm analysis or code plan",
            ]
            if any(any(crit in err for crit in critical_errors) for err in errors):
                return False

        # Stop if retry count exceeded
        if state.get("retry_count", 0) >= state.get("max_retries", 3):
            return False

        return True

    def _determine_next_step(self, state: Dict[str, Any]) -> str:
        """Determine the next step based on current state.

        Args:
            state: Current state

        Returns:
            Name of the next step/agent
        """
        current_step = state.get("current_step", "start")
        errors = state.get("errors", [])

        # Check for errors and decide whether to retry or continue
        if errors and current_step != "start":
            # If validation failed, we could go back to code generation
            if current_step == "validation_completed":
                # Check if we should retry code generation
                if state.get("retry_count", 0) < state.get("max_retries", 3):
                    return "retry_code_generation"
                return "end"
            return "end"

        # Normal flow
        if current_step == "start":
            return "pdf_reading"
        elif current_step == "pdf_reading_completed":
            return "algorithm_analysis"
        elif current_step == "algorithm_analysis_completed":
            return "code_planning"
        elif current_step == "code_planning_completed":
            return "code_generation"
        elif current_step == "code_generation_completed":
            return "validation"
        elif current_step == "validation_completed":
            return "end"
        elif current_step == "retry_code_generation":
            return "code_generation"
        else:
            return "end"

    def run(self, pdf_path: str) -> Dict[str, Any]:
        """Run the complete workflow.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Final state with all results
        """
        # Create initial state
        state = self._create_initial_state(pdf_path)

        # Execute workflow
        while True:
            # Determine next step
            next_step = self._determine_next_step(state)

            if next_step == "end":
                break

            # Execute the next step
            try:
                if next_step == "pdf_reading":
                    state = self.pdf_reader(state)
                    print("✓ PDF reading completed")
                elif next_step == "algorithm_analysis":
                    state = self.algorithm_analyzer(state)
                    print("✓ Algorithm analysis completed")
                elif next_step == "code_planning":
                    state = self.code_planner(state)
                    print("✓ Code planning completed")
                elif next_step == "code_generation":
                    state = self.code_generator(state)
                    print("✓ Code generation completed")
                elif next_step == "validation":
                    state = self.code_validator(state)
                    print("✓ Code validation completed")
                elif next_step == "retry_code_generation":
                    state["retry_count"] = state.get("retry_count", 0) + 1
                    print(f"⚠ Retrying code generation (attempt {state['retry_count']})")
                    # Keep previous generated code for reference
                    state = self.code_generator(state)

                # Check if we should continue
                if not self._should_continue(state):
                    break

            except Exception as e:
                state["errors"].append(f"Workflow error at step {next_step}: {str(e)}")
                print(f"✗ Error at step {next_step}: {str(e)}")

                # Stop on unexpected errors
                if not self._should_continue(state):
                    break

        # Add final status
        if state.get("errors"):
            state["status"] = "failed"
        elif state.get("validation_result", {}).get("status") == "success":
            state["status"] = "success"
        elif state.get("validation_result", {}).get("status") == "failed":
            state["status"] = "validation_failed"
        else:
            state["status"] = "partial"

        return state

    def get_summary(self, state: Dict[str, Any]) -> str:
        """Generate a summary of the workflow execution.

        Args:
            state: Final state

        Returns:
            Summary string
        """
        summary_lines = []
        summary_lines.append("=" * 60)
        summary_lines.append("MultiAgentPaperCoder Execution Summary")
        summary_lines.append("=" * 60)

        # Status
        status = state.get("status", "unknown")
        status_icon = "✓" if status == "success" else "✗"
        summary_lines.append(f"\nStatus: {status_icon} {status}")

        # PDF info
        if state.get("paper_content"):
            paper_content = state["paper_content"]
            summary_lines.append(f"\n📄 Paper: {paper_content.get('title', 'Unknown')}")

        # Algorithm info
        if state.get("algorithm_analysis"):
            algo = state["algorithm_analysis"]
            summary_lines.append(f"\n🧠 Algorithm: {algo.get('algorithm_name', 'Unknown')}")
            summary_lines.append(f"   Type: {algo.get('algorithm_type', 'Unknown')}")

        # Generated code
        if state.get("generated_code"):
            code = state["generated_code"]
            summary_lines.append(f"\n💻 Generated Code:")
            summary_lines.append(f"   Files: {code.get('total_files', 0)}")
            summary_lines.append(f"   Directory: {code.get('code_dir', 'Unknown')}")

        # Validation result
        if state.get("validation_result"):
            val = state["validation_result"]
            summary_lines.append(f"\n✅ Validation:")
            summary_lines.append(f"   Status: {val.get('status', 'Unknown')}")
            summary_lines.append(f"   Time: {val.get('execution_time', 0):.2f}s")

            if val.get("status") == "failed":
                summary_lines.append(f"\n   Error Log (first 500 chars):")
                summary_lines.append(f"   {val.get('error_log', '')[:500]}")

                suggestions = val.get("fix_suggestions", [])
                if suggestions:
                    summary_lines.append(f"\n   Suggestions:")
                    for i, sugg in enumerate(suggestions, 1):
                        summary_lines.append(f"   {i}. {sugg}")

        # Errors
        if state.get("errors"):
            summary_lines.append(f"\n❌ Errors:")
            for error in state["errors"][-5:]:  # Show last 5 errors
                summary_lines.append(f"   - {error}")

        summary_lines.append("\n" + "=" * 60)

        return "\n".join(summary_lines)
