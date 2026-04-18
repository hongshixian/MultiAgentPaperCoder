"""LLM abstraction layer for MultiAgentPaperCoder.

This module provides a unified interface for LLM interactions
with support for streaming and structured output.
"""

from .base import BaseLLM, StreamingOutput
from .llm_client import LLMClient, get_llm

__all__ = ["BaseLLM", "StreamingOutput", "LLMClient", "get_llm"]
