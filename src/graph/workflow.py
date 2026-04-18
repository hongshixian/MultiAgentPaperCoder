"""Workflow orchestration using LangGraph.

This module provides LangGraph-based workflow orchestration
with state management, conditional routing, and loop support.
"""

from typing import Dict, Any
from pathlib import Path
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

import os
from dotenv import load_dotenv

load_dotenv()

from ..state import PaperState


def _generate_output_dir(pdf_path: str, base_dir: str = "./output") -> str:
    """Generate unique output directory based on PDF filename and timestamp.

    Args:
        pdf_path: Path to PDF file
        base_dir: Base output directory

    Returns:
        Path string for unique output directory
    """
    # Extract PDF filename without extension
    pdf_name = Path(pdf_path).stem

    # Create timestamp string
    time_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Combine timestamp and PDF name
    output_name = f"{time_str}_{pdf_name}"

    # Create full path
    return str(Path(base_dir) / output_name)


def _create_initial_state(pdf_path: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create initial state for workflow.

    Args:
        pdf_path: Path to PDF file
        config: Optional configuration dictionary

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
        "verification_result": None,
        "repair_history": [],
        "current_step": "start",
        "errors": [],
        "retry_count": 0,
        "max_retries": config.get("max_retries", 3) if config else 3,
        "iteration_count": 0,
        "max_iterations": 5,
    }


def document_analysis_node(state: PaperState, config: Dict[str, Any] = None) -> PaperState:
    """LangGraph node for document analysis.

    Args:
        state: Current state
        config: Optional configuration dictionary

    Returns:
        Updated state
    """
    from ..agents.document_analysis_agent import DocumentAnalysisAgent

    agent = DocumentAnalysisAgent(config or {})
    result = agent(state)
    print("✓ Document analysis completed")
    return result


def code_generation_node(state: PaperState, config: Dict[str, Any] = None) -> PaperState:
    """LangGraph node for code generation.

    Args:
        state: Current state
        config: Optional configuration dictionary

    Returns:
        Updated state
    """
    from ..agents.code_generation_agent import CodeGenerationAgent

    # Merge provided config with defaults
    agent_config = (config or {}).copy()
    if "output_dir" not in agent_config:
        agent_config["output_dir"] = "./output/generated_code"

    agent = CodeGenerationAgent(agent_config)
    result = agent(state)
    print("✓ Code generation completed")
    return result


def code_verification_node(state: PaperState, config: Dict[str, Any] = None) -> PaperState:
    """LangGraph node for code verification.

    Args:
        state: Current state
        config: Optional configuration dictionary

    Returns:
        Updated state
    """
    from ..agents.code_verification_agent import CodeVerificationAgent

    # Merge provided config with defaults
    agent_config = (config or {}).copy()
    if "conda_env_name" not in agent_config:
        agent_config["conda_env_name"] = os.getenv("CONDA_ENV_NAME", "py12pt")

    agent = CodeVerificationAgent(agent_config)
    result = agent(state)
    validation_status = (result.get("validation_result") or {}).get("status", "unknown")
    verification = result.get("verification_result") or {}
    quality_score = verification.get("quality_score", "N/A")
    print(f"✓ Code verification completed (status: {validation_status}, quality: {quality_score})")
    if verification.get("needs_repair"):
        print(f"  → Needs repair")
    elif verification.get("needs_regeneration"):
        print(f"  → Needs code regeneration")
    return result


def error_repair_node(state: PaperState, config: Dict[str, Any] = None) -> PaperState:
    """LangGraph node for error repair.

    Args:
        state: Current state
        config: Optional configuration dictionary

    Returns:
        Updated state
    """
    from ..agents.error_repair_agent import ErrorRepairAgent

    agent = ErrorRepairAgent(config or {})
    iteration = state.get("iteration_count", 0) + 1
    state["iteration_count"] = iteration
    print(f"⚠ Attempting error repair (iteration {iteration})")
    result = agent(state)
    return result


def should_continue_verification(state: PaperState) -> str:
    """Determine next step after code verification.

    Args:
        state: Current state

    Returns:
        Next step name: "error_repair", "code_regeneration", or "end"
    """
    verification = state.get("verification_result") or {}
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 5)

    # Check for repair needs
    if verification.get("needs_repair"):
        if iteration_count >= max_iterations:
            print("✗ Max iterations reached for repair")
            return "end"
        return "error_repair"

    # Check for regeneration needs
    if verification.get("needs_regeneration"):
        if iteration_count >= max_iterations:
            print("✗ Max iterations reached for regeneration")
            return "end"
        return "code_regeneration"

    # Verification passed
    return "end"


def create_workflow(config: Dict[str, Any] = None) -> StateGraph:
    """Create LangGraph workflow.

    Args:
        config: Optional configuration dictionary

    Returns:
        Compiled StateGraph workflow
    """
    # Store config for use in node functions
    workflow_config = config or {}

    # Create node functions with config captured via closure
    def doc_analysis_node(state: PaperState) -> PaperState:
        return document_analysis_node(state, workflow_config)

    def code_gen_node(state: PaperState) -> PaperState:
        return code_generation_node(state, workflow_config)

    def code_verify_node(state: PaperState) -> PaperState:
        return code_verification_node(state, workflow_config)

    def err_repair_node(state: PaperState) -> PaperState:
        return error_repair_node(state, workflow_config)

    # Create state graph
    workflow = StateGraph(PaperState)

    # Add all nodes
    workflow.add_node("document_analysis", doc_analysis_node)
    workflow.add_node("code_generation", code_gen_node)
    workflow.add_node("code_verification", code_verify_node)
    workflow.add_node("error_repair", err_repair_node)

    # Set entry point
    workflow.set_entry_point("document_analysis")

    # Add sequential edges (normal flow)
    workflow.add_edge("document_analysis", "code_generation")
    workflow.add_edge("code_generation", "code_verification")

    # Add conditional edges after result verification
    workflow.add_conditional_edges(
        "code_verification",
        should_continue_verification,
        {
            "error_repair": "error_repair",
            "code_regeneration": "code_generation",
            "end": END,
        }
    )

    # After repair, go back to verification
    workflow.add_edge("error_repair", "code_verification")

    # Add memory checkpointing for persistence
    memory = MemorySaver()

    return workflow.compile(checkpointer=memory)


class PaperCoderWorkflow:
    """Orchestrates paper coding workflow using LangGraph."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize workflow.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.compiled_graph = create_workflow(self.config)

    def run(self, pdf_path: str, thread_id: str = "default") -> Dict[str, Any]:
        """Run complete workflow.

        Args:
            pdf_path: Path to PDF file
            thread_id: Unique thread ID for checkpointing

        Returns:
            Final state with all results
        """
        # Create initial state
        initial_state = _create_initial_state(pdf_path, self.config)

        # Execute workflow
        final_state = self.compiled_graph.invoke(
            initial_state,
            config={"configurable": {"thread_id": thread_id}}
        )

        # Add final status
        self._add_final_status(final_state)

        return final_state

    def _add_final_status(self, state: Dict[str, Any]):
        """Add final status to state.

        Args:
            state: State to update
        """
        verification_result = state.get("verification_result", {})
        if state.get("errors"):
            state["status"] = "failed"
        elif (
            verification_result.get("status") == "completed"
            and not verification_result.get("needs_regeneration")
            and not verification_result.get("needs_repair")
        ):
            state["status"] = "success"
        elif state.get("validation_result", {}).get("status") == "success":
            state["status"] = "validation_success"  # Code ran but not verified
        elif state.get("validation_result", {}).get("status") == "failed":
            state["status"] = "validation_failed"
        else:
            state["status"] = "partial"

    def get_summary(self, state: Dict[str, Any]) -> str:
        """Generate a summary of workflow execution.

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
            directory = code.get('code_dir', 'Unknown')
            if directory:
                summary_lines.append(f"   Directory: {directory}")

        # Validation result
        if state.get("validation_result"):
            val = state["validation_result"]
            summary_lines.append(f"\n✅ Validation:")
            summary_lines.append(f"   Status: {val.get('status', 'Unknown')}")
            execution_time = val.get("execution_time", 0)
            summary_lines.append(f"   Time: {execution_time:.2f}s")

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
                    files_fixed = len(entry.get("files_fixed", []))
                    summary_lines.append(f"   {i}. Cause: {entry.get('root_cause', 'N/A')}, Fixed: {files_fixed} files")

        # Errors
        if state.get("errors"):
            summary_lines.append(f"\n❌ Errors:")
            for error in state["errors"][-5:]:  # Show last 5 errors
                summary_lines.append(f"   - {error}")

        summary_lines.append("\n" + "=" * 60)

        return "\n".join(summary_lines)
