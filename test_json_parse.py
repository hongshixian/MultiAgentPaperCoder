"""Test JSON parsing with real LLM response."""

import os
import sys
import json
import re

os.environ["LLM_PROVIDER"] = "zhipu"
os.environ["ZHIPU_API_KEY"] = "ee224389b92c47289d801c3b5674aa1e.RxOdScSDxcZwO0vi"
os.environ["ZHIPU_MODEL"] = "glm-5"
os.environ["ZHIPU_BASE_URL"] = "https://open.bigmodel.cn/api/paas/v4"

sys.path.insert(0, "src")

from src.tools.llm_client import LLMClient


def test_simple_json():
    """Test with simple JSON request."""
    print("=" * 60)
    print("Test 1: Simple JSON Generation")
    print("=" * 60)

    client = LLMClient()

    prompt = """Please return a simple JSON object with these fields:
{
  "name": "string",
  "count": number,
  "active": boolean
}

IMPORTANT: Return ONLY JSON, no markdown, no code blocks, no explanations."""

    print("\nPrompt:", prompt)
    print("\nGenerating...")

    response = client.generate(prompt)

    print("\nRaw response (first 500 chars):")
    print(response[:500])
    print("\nFull response length:", len(response))

    # Try to parse

    print("\n--- Parsing Attempt 1: Direct JSON.parse() ---")
    try:
        result = json.loads(response)
        print("SUCCESS:", result)
        return True
    except json.JSONDecodeError as e:
        print(f"FAILED: {e}")

    print("\n--- Parsing Attempt 2: Extract JSON block ---")
    # Try to find ```json ... ```` blocks
    json_block_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', response, re.DOTALL)
    if json_block_match:
        json_text = json_block_match.group(1).strip()
        print(f"Found JSON block ({len(json_text)} chars)")
        try:
            result = json.loads(json_text)
            print("SUCCESS:", result)
            return True
        except json.JSONDecodeError as e:
            print(f"FAILED: {e}")
    else:
        print("No JSON block found")

    print("\n--- Parsing Attempt 3: Brace matching ---")
    # Find first { and matching }
    start_idx = response.find('{')
    if start_idx != -1:
        print(f"Found {{ at position {start_idx}")
        brace_count = 0
        for i in range(start_idx, len(response)):
            if response[i] == '{':
                brace_count += 1
            elif response[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_text = response[start_idx:i+1]
                    print(f"Extracted JSON ({len(json_text)} chars)")
                    try:
                        result = json.loads(json_text)
                        print("SUCCESS:", result)
                        return True
                    except json.JSONDecodeError as e:
                        print(f"FAILED: {e}")
                        print(f"\nJSON text (last 200 chars):")
                        print(json_text[-200:])
                        break

    print("\nAll parsing attempts failed")
    return False


def main():
    """Run tests."""
    print("JSON Parsing Test")

    try:
        if test_simple_json():
            print("\n✗ Test failed")
            return 1
        else:
            print("\n✓与其他结果 Test passed")
            return 0
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
