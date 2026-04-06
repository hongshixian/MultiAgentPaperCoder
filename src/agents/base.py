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
