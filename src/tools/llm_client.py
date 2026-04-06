"""LLM Client for interacting with Claude API."""

import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class LLMConfig:
    """Configuration for LLM client."""

    api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    model: str = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
    max_tokens: int = int(os.getenv("CLAUDE_MAX_TOKENS", "4096"))
    temperature: float = float(os.getenv("CLAUDE_TEMPERATURE", "0.7"))
    timeout: int = int(os.getenv("TIMEOUT_SECONDS", "300"))


class LLMClient:
    """Client for interacting with Claude API."""

    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize LLM client.

        Args:
            config: Optional LLM configuration
        """
        self.config = config or LLMConfig()

        if not self.config.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not set. Please set it in .env file "
                "or as environment variable."
            )

        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=self.config.api_key)
        except ImportError:
            raise ImportError(
                "anthropic package not installed. "
                "Please install it with: pip install anthropic"
            )

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
            max_tokens: Override max_tokens from config
            temperature: Override temperature from config

        Returns:
            Generated text response
        """
        messages = max_tokens if max_tokens is not None else self.config.max_tokens
        temp = temperature if temperature is not None else self.config.temperature

        kwargs = {
            "model": self.config.model,
            "max_tokens": messages,
            "temperature": temp,
            "messages": [{"role": "user", "content": prompt}],
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        try:
            response = self.client.messages.create(**kwargs)
            return response.content[0].text
        except Exception as e:
            raise RuntimeError(f"LLM generation failed: {e}")

    def generate_structured(
        self,
        prompt: str,
        output_format: Dict[str, Any],
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate structured response from LLM.

        Args:
            prompt: User prompt
            output_format: Expected output format (for type hints)
            system_prompt: Optional system prompt

        Returns:
            Parsed structured response
        """
        full_prompt = f"""{prompt}

Please provide your response in a structured format that matches the following schema:
{output_format}

Return your answer as valid JSON that can be parsed with json.loads().
"""

        response = self.generate(full_prompt, system_prompt)

        try:
            import json
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback: try to extract JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass

            raise ValueError(
                f"Failed to parse LLM response as JSON. Response: {response[:500]}..."
            )

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
        kwargs = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        try:
            response_text = ""
            with self.client.messages.stream(**kwargs) as stream:
                for text in stream.text_stream:
                    response_text += text
            return response_text
        except Exception as e:
            raise RuntimeError(f"LLM streaming failed: {e}")
