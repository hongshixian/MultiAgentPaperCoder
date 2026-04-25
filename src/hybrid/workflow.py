"""LangGraph workflow with deterministic routing.

The workflow orchestrates four sub-agent nodes in sequence with a
conditional repair loop. Routing decisions are based entirely on
structured state fields (booleans, enums, counters) — no LLM judgment.
"""

from __future__ import annotations

import logging

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from .agents import (
    code_generation_node,
    code_verification_node,
    document_analysis_node,
    error_repair_node,
)
from .config import Settings
from .state import PaperState

logger = logging.getLogger("papercoder.workflow")


def should_continue_verification(state: PaperState) -> str:
    """Deterministic router: decide what happens after verification.

    Returns:
        "error_repair" if the code needs repair and we haven't exceeded
        the iteration limit; "end" otherwise.
    """
    # If upstream steps failed, terminate
    if state.get("analysis_status") == "failed":
        return "end"
    if state.get("generation_status") == "failed":
        return "end"

    needs_repair = state.get("needs_repair", False)
    iteration = state.get("iteration_count", 0)
    max_iter = state.get("max_iterations", 5)

    if needs_repair and iteration < max_iter:
        logger.info(
            "Routing to error_repair (iteration %d/%d)", iteration + 1, max_iter
        )
        return "error_repair"

    if needs_repair and iteration >= max_iter:
        logger.warning("Max iterations (%d) reached, ending workflow", max_iter)

    return "end"


def create_workflow(settings: Settings) -> StateGraph:
    """Build and compile the LangGraph StateGraph workflow.

    Args:
        settings: Runtime settings (LLM, output dirs, etc.)

    Returns:
        Compiled StateGraph ready for .invoke()
    """
    workflow = StateGraph(PaperState)

    # Node functions with settings captured via closure
    def _doc_analysis(state: PaperState) -> dict:
        return document_analysis_node(state, {"settings": settings})

    def _code_gen(state: PaperState) -> dict:
        return code_generation_node(state, {"settings": settings})

    def _code_verify(state: PaperState) -> dict:
        return code_verification_node(state, {"settings": settings})

    def _err_repair(state: PaperState) -> dict:
        # Increment iteration counter before invoking repair
        updated = {
            "iteration_count": state.get("iteration_count", 0) + 1,
        }
        # Merge the counter update into the state so the repair node sees it
        merged = {**state, **updated}
        return error_repair_node(merged, {"settings": settings})

    workflow.add_node("document_analysis", _doc_analysis)
    workflow.add_node("code_generation", _code_gen)
    workflow.add_node("code_verification", _code_verify)
    workflow.add_node("error_repair", _err_repair)

    # Sequential flow
    workflow.set_entry_point("document_analysis")
    workflow.add_edge("document_analysis", "code_generation")
    workflow.add_edge("code_generation", "code_verification")

    # Conditional loop after verification
    workflow.add_conditional_edges(
        "code_verification",
        should_continue_verification,
        {"error_repair": "error_repair", "end": END},
    )

    # Repair loops back to verification
    workflow.add_edge("error_repair", "code_verification")

    return workflow.compile(checkpointer=MemorySaver())
