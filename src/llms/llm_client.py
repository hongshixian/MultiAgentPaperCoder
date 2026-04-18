"""LLM Client implementing BaseLLM interface.

This module provides LLMClient that fully implements the BaseLLM
interface with proper streaming support.
"""

import os
import json
import re
from typing import Optional, Dict, Any, Generator, AsyncIterator

from .base import BaseLLM, StreamingOutput


def get_llm(provider: str = None, **kwargs):
    """Create a LangChain Chat model based on provider.

    Args:
        provider: "claude" or "zhipu". Defaults to env LLM_PROVIDER or "zhipu".
        **kwargs: Override config values.

    Returns:
        LangChain BaseChatModel instance.
    """
    provider = provider or os.getenv("LLM_PROVIDER", "zhipu")

    if provider == "zhipu":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=kwargs.get("model", os.getenv("ZHIPU_MODEL", "glm-5")),
            api_key=kwargs.get("api_key", os.getenv("ZHIPU_API_KEY", "")),
            base_url=kwargs.get(
                "base_url",
                os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
            ),
            max_tokens=kwargs.get("max_tokens", int(os.getenv("LLM_MAX_TOKENS", "4096"))),
            temperature=kwargs.get("temperature", float(os.getenv("LLM_TEMPERATURE", "0.7"))),
            timeout=kwargs.get("timeout", int(os.getenv("TIMEOUT_SECONDS", "300"))),
        )
    else:  # claude
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=kwargs.get("model", os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")),
            api_key=kwargs.get("api_key", os.getenv("ANTHROPIC_API_KEY", "")),
            max_tokens=kwargs.get("max_tokens", int(os.getenv("LLM_MAX_TOKENS", "4096"))),
            temperature=kwargs.get("temperature", float(os.getenv("LLM_TEMPERATURE", "0.7"))),
            timeout=kwargs.get("timeout", int(os.getenv("TIMEOUT_SECONDS", "300"))),
        )


class LLMClient(BaseLLM):
    """LLM client implementing BaseLLM interface.

    This class provides a complete implementation of the BaseLLM
    interface with proper streaming support and structured output.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize LLM client.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        self.llm = get_llm(**self.config)

    def _build_messages(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ):
        """Build message list for LangChain.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt

        Returns:
            List of message objects
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))
        return messages

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """Generate response from LLM.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Override max_tokens
            temperature: Override temperature
            **kwargs: Additional LLM-specific parameters

        Returns:
            Generated text response
        """
        messages = self._build_messages(prompt, system_prompt)

        llm_kwargs = {}
        if max_tokens is not None:
            llm_kwargs["max_tokens"] = max_tokens
        if temperature is not None:
            llm_kwargs["temperature"] = temperature
        llm_kwargs.update(kwargs)

        response = self.llm.invoke(messages, **llm_kwargs)
        return response.content

    def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> Generator[StreamingOutput, None, None]:
        """Generate response with streaming.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Override max_tokens
            temperature: Override temperature
            **kwargs: Additional LLM-specific parameters

        Yields:
            StreamingOutput objects with incremental updates
        """
        messages = self._build_messages(prompt, system_prompt)

        llm_kwargs = {}
        if max_tokens is not None:
            llm_kwargs["max_tokens"] = max_tokens
        if temperature is not None:
            llm_kwargs["temperature"] = temperature
        llm_kwargs.update(kwargs)

        output = StreamingOutput()
        for chunk in self.llm.stream(messages, **llm_kwargs):
            if chunk.content:
                output.add_chunk(chunk.content)
                yield output

        # Final yield to ensure last content is included
        if output.text:
            output.finish_reason = "stop"
            yield output

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
        messages = self._build_messages(prompt, system_prompt)

        llm_kwargs = {}
        if max_tokens is not None:
            llm_kwargs["max_tokens"] = max_tokens
        if temperature is not None:
            llm_kwargs["temperature"] = temperature
        llm_kwargs.update(kwargs)

        output = StreamingOutput()
        async for chunk in self.llm.astream(messages, **llm_kwargs):
            if chunk.content:
                output.add_chunk(chunk.content)
                yield output

        # Final yield
        if output.text:
            output.finish_reason = "stop"
            yield output

    def generate_structured(
        self,
        prompt: str,
        output_format: Dict[str, Any],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate structured JSON response.

        Args:
            prompt: User prompt
            output_format: Expected output format schema
            system_prompt: Optional system prompt
            **kwargs: Additional LLM-specific parameters

        Returns:
            Parsed JSON response as dictionary
        """
        full_prompt = f"""{prompt}

Please provide your response in a structured format that matches the following schema:
{output_format}

Return your answer as valid JSON that can be parsed with json.loads().
"""
        response = self.generate(full_prompt, system_prompt, **kwargs)
        return self._parse_json(response)

    # -- JSON parsing utilities --

    @staticmethod
    def _parse_json(response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response with robust fallback strategies."""
        # 1. Direct parse
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # 2. Extract from ```json ... ``` code block
        match = re.search(r"```(?:json)?\s*\n(.*?)\n```", response, re.DOTALL)
        if match:
            try:
                return LLMClient._parse_robust(match.group(1).strip())
            except ValueError:
                pass

        # 3. Find first balanced { ... }
        start = response.find("{")
        if start != -1:
            depth = 0
            for i in range(start, len(response)):
                if response[i] == "{":
                    depth += 1
                elif response[i] == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            return LLMClient._parse_robust(response[start : i + 1])
                        except ValueError:
                            pass
                        break

        raise ValueError(
            f"Failed to parse LLM response as JSON. "
            f"Response length: {len(response)}. "
            f"First 200 chars: {response[:200]}"
        )

    @staticmethod
    def _parse_robust(text: str) -> Dict[str, Any]:
        """Parse JSON with trailing-comma and comment fixes."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Remove trailing commas
        text = re.sub(r",\s*([}\]])", r"\1", text)
        # Remove line comments
        text = re.sub(r"//.*?$", "", text, flags=re.MULTILINE)
        # Remove block comments
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON parse failed at line {e.lineno}, col {e.col}: {e.msg}")
