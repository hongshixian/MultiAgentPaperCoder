"""Base agent class for all agents in MultiAgentPaperCoder."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(self, name: str, config: Dict[str, Any] = None):
        """Initialize the agent.

        Args:
            name: Name of the agent
            config: Optional configuration dictionary
        """
        self.name = name
        self.config = config or {}

    @abstractmethod
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent with given state.

        Args:
            state: Current state of the paper processing workflow

        Returns:
            Updated state
        """
        pass

    @property
    def agent_name(self) -> str:
        """Return the agent name."""
        return self.name

    def _error_state(self, state: Dict[str, Any], message: str) -> Dict[str, Any]:
        """Return state with appended error message.

        Args:
            state: Current state
            message: Error message to append

        Returns:
            Updated state with error message added to errors list
        """
        errors = state.get("errors", []) + [f"[{self.name}] {message}"]
        return {**state, "errors": errors}

    def _success_state(
        self, state: Dict[str, Any], updates: Dict[str, Any], step: str
    ) -> Dict[str, Any]:
        """Return state with updates and current_step set.

        Args:
            state: Current state
            updates: Dictionary of state updates
            step: Name of the completed step

        Returns:
            Updated state with updates applied and current_step set
        """
        return {**state, **updates, "current_step": step}
