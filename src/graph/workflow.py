"""Workflow orchestration using LangGraph."""

from typing import Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()


class PaperCoderWorkflow:
    """Orchestrates paper coding workflow with support for iterative repair."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize workflow.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}

        # Import agents here to avoid circular imports
        from ..agents.pdf_reader import PDFReaderAgent
        from ..agents.algorithm_analyzer import AlgorithmAnalyzerAgent
        from ..agents.code_planner import CodePlannerAgent
        from ..agents.code_generator import CodeGeneratorAgent
        from ..agents.env_config_agent import EnvConfigAgent
        from ..agents.code_validator import CodeValidatorAgent
        from ..agents.result_verification_agent import ResultVerificationAgent
        from ..agents.error_repair_agent import ErrorRepairAgent

        # Initialize agents
        self.pdf_reader = PDFReaderAgent(self.config)
        self.algorithm_analyzer = AlgorithmAnalyzerAgent(self.config)
        self.code_planner = CodePlannerAgent(self.config)
        self.code_generator = CodeGeneratorAgent({
            **self.config,
            "output_dir": self.config.get("output_dir", "./output/generated_code"),
        })
        self.env_config_agent = EnvConfigAgent(self.config)
        self.code_validator = CodeValidatorAgent({
            **self.config,
            "conda_env_name": self.config.get("conda_env_name", "py12pt"),
        })
        self.result_verification_agent = ResultVerificationAgent(self.config)
        self.error_repair_agent = ErrorRepairAgent(self.config)

    def _create_initial_state(self, pdf_path: str) -> Dict[str, Any]:
        """Create initial state for workflow.

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
            "env_config": None,
            "validation_result": None,
            "verification_result": None,
            "repair_history": [],
            "current_step": "start",
            "errors": [],
            "retry_count": 0,
            "max_retries": self.config.get("max_retries", 3),
            "iteration_count": 0,
            "max_iterations": 5,
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

        # Stop if iteration count exceeded
        iteration_count = state.get("iteration_count", 0)
        max_iterations = state.get("max_iterations", 5)
        if iteration_count >= max_iterations:
            return False

        return True

    def _determine_next_step(self, state: Dict[str, Any]) -> str:
        """Determine next step based on current state.

        Args:
            state: Current state

        Returns:
            Name of the next step/agent
        """
        current_step = state.get("current_step", "start")
        errors = state.get("errors", [])

        # Check for critical errors
        critical_errors = [
            "PDF file not found",
            "Paper content not available",
            "Algorithm analysis not available",
            "Missing algorithm analysis or code plan",
        ]
        if any(any(crit in err for crit in critical_errors) for err in errors):
            return "end"

        # Check if we should continue
        iteration_count = state.get("iteration_count", 0)
        max_iterations = state.get("max_iterations", 5)

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
            return "env_config"
        elif current_step == "env_config_completed":
            return "validation"
        elif current_step == "validation_completed":
            return "result_verification"
        elif current_step == "result_verification_completed":
            # Check verification result
            verification = state.get("verification_result", {})
            if verification.get("needs_repair"):
                # Repair needed - check iteration count
                if iteration_count >= max_iterations:
                    return "end"
                return "error_repair"
            elif verification.get("needs_regeneration"):
                # Regeneration needed - check iteration count
                if iteration_count >= max_iterations:
                    return "end"
                return "code_generation_regenerate"
            else:
                # Results are good, end successfully
                return "end"
        elif current_step == "error_repair_completed":
            # After repair, go back to validation
            return "validation"
        elif current_step == "code_generation_regenerate":
            # After regen, go to code generation
            return "code_generation"
        else:
            return "end"

    def run(self, pdf_path: str) -> Dict[str, Any]:
        """Run the complete workflow.

        Args:
            pdf_path: Path to the PDF file

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

            # Execute next step
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
                elif next_step == "env_config":
                    state = self.env_config_agent(state)
                    print("✓ Environment configuration completed")
                elif next_step == "validation":
                    state = self.code_validator(state)
                    validation_status = state.get("validation_result", {}).get("status", "unknown")
                    print(f"✓ Code validation completed (status: {validation_status})")
                elif next_step == "result_verification":
                    state = self.result_verification_agent(state)
                    verification = state.get("verification_result", {})
                    quality_score = verification.get("quality_score", "N/A")
                    print(f"✓ Result verification completed (quality: {quality_score})")
                    if verification.get("needs_repair"):
                        print(f"  → Needs repair")
                    elif verification.get("needs_regeneration"):
                        print(f"  → Needs code regeneration")
                elif next_step == "error_repair":
                    iteration = state.get("iteration_count", 0) + 1
                    state["iteration_count"] = iteration
                    print(f"⚠ Attempting error repair (iteration {iteration})")
                    state = self.error_repair_agent(state)
                elif next_step == "code_generation_regenerate":
                    iteration = state.get("iteration_count", 0) + 1
                    state["iteration_count"] = iteration
                    print(f"⚠ Regenerating code (iteration {iteration})")
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
        verification_result = state.get("verification_result", {})
        if state.get("errors"):
            state["status"] = "failed"
        elif verification_result.get("status") == "completed" and not verification_result.get("needs_regeneration") and not verification_result.get("needs_repair"):
            state["status"] = "success"
        elif state.get("validation_result", {}).get("status") == "success":
            state["status"] = "validation_success"  # Code ran but not verified
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
        status_icon = "✓" if "success" in status else "✗"
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

        # Verification result
        if state.get("verification_result"):
            verification = state["verification_result"]
            if verification.get("status") == "completed":
                summary_lines.append(f"\n📊 Result Verification:")
                summary_lines.append(f"   Quality Score: {verification.get('quality_score', 'N/A')}")
                summary_lines.append(f"   Assessment: {verification.get('assessment', 'N/A')}")

                if verification.get("needs_repair") or verification.get("needs_regeneration"):
                    suggestions = verification.get("suggestions", [])
                    if suggestions:
                        summary_lines.append(f"\n   Suggestions:")
                        for i, sugg in enumerate(suggestions, 1):
                            summary_lines.append(f"   {i}. {sugg}")

        # Repair history
        if state.get("repair_history"):
            repair_history = state["repair_history"]
            if repair_history:
                summary_lines.append(f"\n🔧 Repair Attempts: {len(repair_history)}")
                for i, entry in enumerate(repair_history, 1):
                    summary_lines.append(f"   {i}. Cause: {entry.get('root_cause', 'N/A')}, Fixed: {len(entry.get('files_fixed', []))} files")

        # Errors
        if state.get("errors"):
            summary_lines.append(f"\n❌ Errors:")
            for error in state["errors"][-5:]:  # Show last 5 errors
                summary_lines.append(f"   - {error}")

        summary_lines.append("\n" + "=" * 60)

        return "\n".join(summary_lines)
