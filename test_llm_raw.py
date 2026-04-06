"""Test raw LLM response to see what we're getting."""

import os
import sys

os.environ["LLM_PROVIDER"] = "zhipu"
os.environ["ZHIPU_API_KEY"] = "ee224389b92c47289d801c3b5674aa1e.RxOdScSDxcZwO0vi"
os.environ["ZHIPU_MODEL"] = "glm-5"
os.environ["ZHIPU_BASE_URL"] = "https://open.bigmodel.cn/api/paas/v4"

sys.path.insert(0, "src")

from src.tools.llm_client import LLMClient


def main():
    """Test raw LLM response."""
    print("=" * 60)
    print("Testing Raw LLM Response")
    print("=" * 60)

    client = LLMClient()

    # Test prompt that's similar to code generation
    prompt = """Generate a simple JSON with 3 files.

IMPORTANT: Return ONLY JSON object, no markdown, no explanations.

JSON Format:
{
  "files": [
    {
      "path": "file1.py",
      "content": "print('hello')"
    },
    {
      "path": "file2.py",
      "content": "x = 1 + 2"
    },
    {
      "path": "file3.py",
      "content": "def foo(): return 42"
    }
  ],
  "summary": "Test summary"
}"""

    print("\nGenerating response...")
    print("(This will show the raw response)\n")

    response = client.generate(prompt)

    print("Raw response:")
    print("-" * 60)
    print(response)
    print("-" * 60)
    print(f"\nResponse length: {len(response)}")

    # Check for escaped quotes
    print("\nChecking for escaped quotes...")
    if '\\"' in response:
        print("Found escaped backslashes! Count:", response.count('\\"'))
        print("First 500 chars after first escape:")
        idx = response.find('\\"')
        if idx > 0:
            print(response[max(0, idx-100):idx+400])

    # Try to parse as-is
    print("\n" + "=" * 60)
    print("Attempting JSON parsing...")
    print("=" * 60)

    import json
    import re

    try:
        result = json.loads(response)
        print("✓ Direct parsing SUCCESS!")
        print("Result keys:", list(result.keys()))
        return 0
    except json.JSONDecodeError as e:
        print(f"✗ Direct: {e}")

    # Try after removing backslashes
    print("\n" + "-" * 60)
    print("Attempting after removing backslashes...")
    print("-" * 60)

    cleaned = response.replace('\\"', '"')
    try:
        result = json.loads(cleaned)
        print("✓ After removing backslashes SUCCESS!")
        print("Result keys:", list(result.keys()))
        return 0
    except json.JSONDecodeError as e:
        print(f"✗ After removing backslashes: {e}")
        print(f"Cleaned sample (first 500 chars):")
        print(cleaned[:500])

    print("\n✗ All parsing attempts failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
