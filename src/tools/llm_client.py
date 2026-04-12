"""LLM Client using LangChain for unified API access."""

import os
import json
import re
from typing import Optional, Dict, Any

from dotenv import load_dotenv

load_dotenv()


def get_llm(provider: str = None, **kwargs):
    """Create a LangChain Chat model based on provider.

    Args:
        provider: "claude" or "zhipu". Defaults to env LLM_PROVIDER or "claude".
        **kwargs: Override config values.

    Returns:
        LangChain BaseChatModel instance.
    """
    provider = provider or os.getenv("LLM_PROVIDER", "claude")

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
    else:
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=kwargs.get("model", os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")),
            api_key=kwargs.get("api_key", os.getenv("ANTHROPIC_API_KEY", "")),
            max_tokens=kwargs.get("max_tokens", int(os.getenv("LLM_MAX_TOKENS", "4096"))),
            temperature=kwargs.get("temperature", float(os.getenv("LLM_TEMPERATURE", "0.7"))),
            timeout=kwargs.get("timeout", int(os.getenv("TIMEOUT_SECONDS", "300"))),
        )


class LLMClient:
    """Client for interacting with LLM APIs via LangChain.

    Maintains the same public interface as the original implementation
    but delegates to LangChain Chat models internally.
    """

    def __init__(self, config=None):
        self.llm = get_llm()

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Generate response from LLM.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Override max_tokens
            temperature: Override temperature

        Returns:
            Generated text response
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        kwargs = {}
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if temperature is not None:
            kwargs["temperature"] = temperature

        response = self.llm.invoke(messages, **kwargs)
        return response.content

    def generate_structured(
        self,
        prompt: str,
        output_format: Dict[str, Any],
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate structured JSON response from LLM.

        Args:
            prompt: User prompt
            output_format: Expected output format (for type hints in prompt)
            system_prompt: Optional system prompt

        Returns:
            Parsed structured response as dict
        """
        full_prompt = f"""{prompt}

Please provide your response in a structured format that matches the following schema:
{output_format}

Return your answer as valid JSON that can be parsed with json.loads().
"""
        response = self.generate(full_prompt, system_prompt)
        return self._parse_json(response)

    def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Generate response with streaming.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt

        Returns:
            Complete response text
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        chunks = []
        for chunk in self.llm.stream(messages):
            chunks.append(chunk.content)
        return "".join(chunks)

    # -- JSON parsing utilities (preserved from original) --

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
            raise ValueError(f"JSON parse failed at line {e.lineno}, col {e.colno}: {e.msg}")
