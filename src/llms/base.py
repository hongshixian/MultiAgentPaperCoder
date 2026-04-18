"""Base LLM abstraction for MultiAgentPaperCoder.

This module provides the abstract base class for LLM implementations
and the StreamingOutput data class for streaming responses.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Generator, AsyncIterator, List


@dataclass
class StreamingOutput:
    """Container for streaming LLM output.

    This class encapsulates the streaming response from an LLM,
    including chunks, delta updates, and metadata.
    """

    # Accumulated chunks from the stream
    chunks: List[str] = field(default_factory=list)

    # Delta updates (incremental content)
    delta: str = ""

    # Complete text (joined chunks)
    text: str = ""

    # Finish reason (stop, length, error, etc.)
    finish_reason: Optional[str] = None

    # Usage statistics
    usage_stats: Dict[str, Any] = field(default_factory=dict)

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Compute text from chunks after initialization."""
        if not self.text and self.chunks:
            self.text = "".join(self.chunks)

    def add_chunk(self, chunk: str):
        """Add a chunk to the streaming output.

        Args:
            chunk: Text chunk to add
        """
        if chunk:
            self.chunks.append(chunk)
            self.delta = chunk
            self.text += chunk


class BaseLLM(ABC):
    """Abstract base class for LLM implementations.

    All LLM clients should inherit from this class and implement
    the required methods.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the LLM client.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """Generate a complete response from the LLM.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Override max_tokens
            temperature: Override temperature
            **kwargs: Additional LLM-specific parameters

        Returns:
            Complete text response
        """
        pass

    @abstractmethod
    def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> Generator[StreamingOutput, None, None]:
        """Generate a streaming response from the LLM.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Override max_tokens
            temperature: Override temperature
            **kwargs: Additional LLM-specific parameters

        Yields:
            StreamingOutput objects with incremental updates
        """
        pass

    @abstractmethod
    async def astream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> AsyncIterator[StreamingOutput]:
        """Generate a streaming response asynchronously.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Override max_tokens
            temperature: Override temperature
            **kwargs: Additional LLM-specific parameters

        Yields:
            StreamingOutput objects with incremental updates
        """
        pass

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        output_format: Dict[str, Any],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a structured JSON response.

        Args:
            prompt: User prompt
            output_format: Expected output format schema
            system_prompt: Optional system prompt
            **kwargs: Additional LLM-specific parameters

        Returns:
            Parsed JSON response as dictionary
        """
        pass

    def sync_stream_to_string(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> StreamingOutput:
        """Stream and return complete output as StreamingOutput.

        This is a convenience method that consumes the entire stream
        and returns the final StreamingOutput object.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            **kwargs: Additional LLM-specific parameters

        Returns:
            Complete StreamingOutput object
        """
        output = StreamingOutput()
        for chunk_output in self.stream_generate(prompt, system_prompt, **kwargs):
            output.add_chunk(chunk_output.delta)
        return output

    async def async_stream_to_string(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> StreamingOutput:
        """Async stream and return complete output as StreamingOutput.

        This is a convenience method that consumes the entire async stream
        and returns the final StreamingOutput object.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            **kwargs: Additional LLM-specific parameters

        Returns:
            Complete StreamingOutput object
        """
        output = StreamingOutput()
        async for chunk_output in self.astream_generate(prompt, system_prompt, **kwargs):
            output.add_chunk(chunk_output.delta)
        return output
