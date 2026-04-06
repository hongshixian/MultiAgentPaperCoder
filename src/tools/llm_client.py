"""LLM Client for interacting with LLM APIs (Claude, ZhipuAI, etc.)."""

import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from dotenv import load_dotenv
import json

load_dotenv()


@dataclass
class LLMConfig:
    """Configuration for LLM client."""

    # Provider selection
    provider: str = os.getenv("LLM_PROVIDER", "claude")  # Options: claude, zhipu

    # Claude Configuration
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    claude_model: str = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")

    # ZhipuAI Configuration
    zhipu_api_key: str = os.getenv("ZHIPU_API_KEY", "")
    zhipu_model: str = os.getenv("ZHIPU_MODEL", "glm-5")
    # Note: OpenAI SDK will append /chat/completions to this base URL
    zhipu_base_url: str = os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")

    # Common Configuration
    max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "4096"))
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    timeout: int = int(os.getenv("TIMEOUT_SECONDS", "300"))

    @property
    def api_key(self) -> str:
        """Get the appropriate API key based on provider."""
        if self.provider == "zhipu":
            return self.zhipu_api_key
        else:
            return self.anthropic_api_key

    @property
    def model(self) -> str:
        """Get the appropriate model based on provider."""
        if self.provider == "zhipu":
            return self.zhipu_model
        else:
            return self.claude_model


class LLMClient:
    """Client for interacting with LLM APIs."""

    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize LLM client.

        Args:
            config: Optional LLM configuration
        """
        self.config = config or LLMConfig()

        if not self.config.api_key:
            raise ValueError(
                f"{self.config.provider.upper()}_API_KEY not set. "
                f"Please set it in .env file or as environment variable."
            )

        # Initialize appropriate client
        if self.config.provider == "zhipu":
            self._init_zhipu_client()
        else:
            self._init_claude_client()

    def _init_claude_client(self):
        """Initialize Claude API client."""
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=self.config.api_key)
        except ImportError:
            raise ImportError(
                "anthropic package not installed. "
                "Please install it with: pip install anthropic"
            )

    def _init_zhipu_client(self):
        """Initialize ZhipuAI API client (OpenAI compatible)."""
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.zhipu_base_url
            )
        except ImportError:
            raise ImportError(
            "openai package not installed. "
                "Please install it with: pip install openai"
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
        if self.config.provider == "zhipu":
            return self._generate_zhipu(prompt, system_prompt, max_tokens, temperature)
        else:
            return self._generate_claude(prompt, system_prompt, max_tokens, temperature)

    def _generate_claude(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Generate response using Claude API."""
        messages = max_tokens if max_tokens is not None else self.config.max_tokens
        temp = temperature if temperature is not None else self.config.temperature

        kwargs = {
            "model": self.config.claude_model,
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
            raise RuntimeError(f"Claude generation failed: {e}")

    def _generate_zhipu(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Generate response using ZhipuAI API."""
        messages = max_tokens if max_tokens is not None else self.config.max_tokens
        temp = temperature if temperature is not None else self.config.temperature

        # Build messages
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})
        api_messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.config.zhipu_model,
                messages=api_messages,
                max_tokens=messages,
                temperature=temp,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"ZhipuAI generation failed: {e}")

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
            import re

            # Try to find JSON in response
            # First, try direct parsing
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                pass

            # Try to find JSON code block (```json ... ```) - non-greedy to get first block
            json_block_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', response, re.DOTALL)
            if json_block_match:
                json_text = json_block_match.group(1).strip()
                try:
                    return json.loads(json_text)
                except json.JSONDecodeError:
                    # Try to fix common JSON issues
                    # Remove trailing commas
                    json_text = re.sub(r',\s*([}\]])', r'\1', json_text)
                    return json.loads(json_text)

            # Try to find JSON object from first { to matching }
            start_idx = response.find('{')
            if start_idx != -1:
                brace_count = 0
                for i in range(start_idx, len(response)):
                    if response[i] == '{':
                        brace_count += 1
                    elif response[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_text = response[start_idx:i+1]
                            return json.loads(json_text)

            raise ValueError(
                f"Failed to parse LLM response as JSON. Response: {response[:500]}..."
            )
        except Exception as e:
            raise ValueError(
                f"Failed to parse LLM response as JSON. Error: {str(e)}. Response: {response[:500]}..."
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
        if self.config.provider == "zhipu":
            return self._stream_generate_zhipu(prompt, system_prompt)
        else:
            return self._stream_generate_claude(prompt, system_prompt)

    def _stream_generate_claude(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Generate response with streaming using Claude API."""
        kwargs = {
            "model": self.config.claude_model,
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
            raise RuntimeError(f"Claude streaming failed: {e}")

    def _stream_generate_zhipu(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Generate response with streaming using ZhipuAI API."""
        # Build messages
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})
        api_messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.config.zhipu_model,
                messages=api_messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                stream=True,
            )
            response_text = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    response_text += chunk.choices[0].delta.content
            return response_text
        except Exception as e:
            raise RuntimeError(f"ZhipuAI streaming failed: {e}")
