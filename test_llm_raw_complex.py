"""Test with complex prompt that causes issues."""

import os
import sys

os.environ["LLM_PROVIDER"] = "zhipu"
os.environ["ZHIPU_API_KEY"] = "ee224389b92c47289d801c3b5674aaari.RxOdScSDxcZwO0vi"
os.environ["ZHIPU_MODEL"] = "glm-5"
os.environ["ZHIPU_BASE_URL"] = "https://open.bigmodel.cn/api/paas/v4"

sys.path.insert(0, "src")

from src.tools.llm_client import LLMClient


def test_complex_prompt():
    """Test with complex code generation prompt."""
    print("=" * 60)
    print("Testing Complex Code Generation Prompt")
    print("=" * 60)

    client = LLMClient()

    # Simplified complex prompt
    prompt = """Generate Python code for a linear regression model.

IMPORTANT: Return ONLY valid JSON, no markdown, no explanations.

JSON Format:
{{
  "name": "LinearRegression",
  "file_content": "complete python code here"
}}"""

    print("\nPrompt (first 200 chars):")
    print(prompt[:200] + "...")
    print("\nGenerating...")

    response = client.generate(prompt)

    print("\nRaw response (first 500 chars):")
    print(response[:500])
    print(f"\nFull response length: {len(response)}")

    # Count backslashes
    print(f"\nBackslash count: {response.count('\')}")
    print(f"Quote count: {response.count('"')}")

    # Try to parse
    import json
    import re

    print("\n" + "=" * 60)
    print("Parsing Attempts")
    print("=" * 60)

    # Attempt 1: Direct
    print("\nAttempt 1: Direct json.loads()")
    try:
        result = json.loads(response)
        print("✓ SUCCESS!")
        print("Keys:", list(result.keys()))
        return True
    except json.JSONDecodeError as e:
        print(f"✗ FAILED: {e}")

    # Attempt 2: Remove markdown
    print("\nAttempt 2: Remove markdown code blocks")
    cleaned = re.sub(r'```(?:json)?\s*', '', response)
    print(f"Cleaned (first 200 chars): {cleaned[:200]}...")
    try:
        result = json.loads(cleaned)
        print("✓ SUCCESS!")
        print("Keys:", list(result.keys()))
        return True
    except json.JSONDecodeError as e:
        print(f"✗ FAILED: {e}")

    # Attempt 3: Fix backslashes
    print("\nAttempt 3: Fix escaped backslashes")
    # Replace escaped quotes
    fixed = cleaned.replace('\\"', '"')
    print(f"Fixed (first 200 chars): {fixed[:200]}...")
    try:
        result = json.loads(fixed)
        print("✓ SUCCESS!")
        print("Keys:", list(result.keys()))
        return True
    except json.JSONDecodeError as e:
        print(f"✗ FAILED: {e}")
        print(f"Error position: {e.pos if hasattr(e, 'pos') else 'N/A'}")
        if hasattr(e, 'pos') and e.pos:
            print(f"Context around error: {fixed[max(0, e.pos-30):e.pos+30]}")

    print("\n✗ All attempts failed")
    return False


def main():
    """Run test."""
    print("Complex LLM Response Test")

    try:
        if test_complex_prompt():
            print("\n✓ Test passed!")
            return 0
        else:
            print("\n✗ Test failed")
            return 1
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
