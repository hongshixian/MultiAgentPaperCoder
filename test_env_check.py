"""Check if dotenv loads correctly."""

import os
from dotenv import load_dotenv

print("Before load_dotenv():")
print(f"  LLM_MAX_TOKENS env var: {os.getenv('LLM_MAX_TOKENS')}")

load_dotenv()
print("\nAfter load_dotenv() (without override=True):")
print(f"  LLM_MAX_TOKENS env var: {os.getenv('LLM_MAX_TOKENS')}")

# Now set env var and load again
os.environ["LLM_MAX_TOKENS"] = "9999"
print("\nAfter setting env var to 9999:")
print(f"  LLM_MAX_TOKENS env var: {os.getenv('LLM_MAX_TOKENS')}")

load_dotenv()
print("\nAfter load_dotenv() again (without override=True):")
print(f"  LLM_MAX_TOKENS env var: {os.getenv('LLM_MAX_TOKENS')}")

load_dotenv(override=True)
print("\nAfter load_dotenv(override=True):")
print(f"  LLM_MAX_TOKENS env var: {os.getenv('LLM_MAX_TOKENS')}")
