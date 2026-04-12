"""Check actual config values used."""

import sys
sys.path.insert(0, "src")

from src.tools.llm_client import LLMConfig

config = LLMConfig()

print("Current LLM Configuration:")
print(f"  Provider: {config.provider}")
print(f"  Max Tokens: {config.max_tokens}")
print(f"  Temperature: {config.temperature}")
print(f"  Timeout: {config.timeout}")
print(f"  API Key (first 10 chars): {config.api_key[:10]}...")
print(f"  Model: {config.model}")
