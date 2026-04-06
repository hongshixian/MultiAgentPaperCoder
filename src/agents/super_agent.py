"""Super Agent for coordinating sub-agents."""

from typing import Dict, Any

from .base import BaseAgent


class PaperCoderSuperAgent(BaseAgent):
    """Super agent that coordinates sub-agents and manages overall workflow."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize super agent.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__("PaperCoderSuper", config)

        # This agent is primarily for coordination
        # The actual workflow is handled by PaperCoderWorkflow

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate the workflow (delegated to workflow module).

        Note: This agent is a placeholder for the super agent concept.
        The actual coordination is done by PaperCoderWorkflow.

        Args:
            state: Current state

        Returns:
            Updated state
        """
        # The super agent delegates to the workflow
        # This is called by the workflow module
        return state

    def get_status(self, state: Dict[str, Any]) -> str:
        """Get current workflow status.

        Args:
            state: Current state

        Returns:
            Status string
        """
        current_step = state.get("current_step", "unknown")
        errors = state.get("errors", [])

        if errors and current_step != "start":
            return "error"
        elif current_step == "validation_completed":
            return "completed"
        else:
            return current_step
