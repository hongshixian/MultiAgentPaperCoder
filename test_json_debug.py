"""Debug JSON parsing issue."""

import os
import sys

os.environ["LLM_PROVIDER"] = "zhipu"
os.environ["ZHIPU_API_KEY"] = "ee224389b92c47289d801c3b5674aa1e.RxOdScSDxcZwO0vi"
os.environ["ZHIPU_MODEL"] = "glm-5"
os.environ["ZHIPU_BASE_URL"] = "https://open.bigmodel.cn/api/paas/v4"
os.environ["LLM_MAX_TOKENS"] = "16384"

sys.path.insert(0, "src")

from src.tools.llm_client import LLMClient
import json
import re

# Prepare the same prompt as in code_generator.py
prompt = """You are an expert developer specializing in machine learning implementations. Generate production-ready, well-documented code.

Algorithm Information:
Algorithm Name: Simple Linear Regression
Algorithm Type: regression

Core Logic:
Minimizes MSE loss using gradient descent

Hyperparameters: {'learning_rate': '0.01', 'max_iterations': '1000'}

Implementation Plan:
Project Structure:
  - main.py: Main training script
  - model.py: Model definition
  - config.py: Configuration file

Implementation Steps:
  1. Step 1: Create config.py with hyperparameters
  2. Step 2: Implement LinearRegression class
  3. Step 3: Create main.py with training loop

Dependencies:
- Python: numpy>=1.21.0
- System:

Entry Points: main.py

Generate complete, runnable Python code for each file in the project structure. Follow best practices:
- Include comprehensive docstrings
- Use type hints where appropriate
- Handle errors gracefully
- Include logging configuration
- Make code modular and reusable
- Add comments for complex logic

For each file, provide:
1. Complete file path (relative)
2. Full file content (no partial code)

Provide your response as a structured JSON with these fields:
- files: list of dicts with fields:
  - path: string (relative path from project root)
  - content: string (complete file content)
- requirements_txt: string (optional, content for requirements.txt)
- summary: string (brief summary of generated code)

Please provide your response in a structured format that matches the following schema:
{'files': [{'path': 'string', 'content': 'string'}], 'requirements_txt': 'string', 'summary': 'string'}

Return your answer as valid JSON that can be parsed with json.loads()."""

system_prompt = """You are an expert Python developer. Generate clean, production-ready code that follows best practices. Include proper error handling, logging, and documentation. Always respond in valid JSON format."""

print("Generating response from LLM...")
client = LLMClient()
response = client.generate(prompt, system_prompt)

print(f"\nResponse length: {len(response)} characters")
print(f"\nFirst 200 chars:\n{response[:200]}")
print(f"\nLast 200 chars:\n{response[-200:]}")

# Try different parsing methods
print("\n" + "=" * 60)
print("Attempting JSON parsing...")
print("=" * 60)

# Method 1: Direct parsing
try:
    result = json.loads(response)
    print("\n✓ Method 1 (Direct parsing): SUCCESS")
    print(f"Files found: {len(result.get('files', []))}")
    for f in result.get('files', [])[:3]:
        print(f"  - {f.get('path')}: {len(f.get('content', ''))} chars")
except json.JSONDecodeError as e:
    print(f"\n✗ Method 1 (Direct parsing): FAILED - {e}")

# Method 2: Find JSON code block
json_block_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', response, re.DOTALL)
if json_block_match:
    json_text = json_block_match.group(1).strip()
    print(f"\n✓ Found JSON code block ({len(json_text)} chars)")
    try:
        result = json.loads(json_text)
        print(f"✓ Method 2 (Code block parsing): SUCCESS")
        print(f"Files found: {len(result.get('files', []))}")
        for f in result.get('files', [])[:3]:
            print(f"  - {f.get('path')}: {len(f.get('content', ''))} chars")
    except json.JSONDecodeError as e:
        print(f"✗ Method 2 (Code block parsing): FAILED - {e}")
        print(f"First 200 chars of JSON block:\n{json_text[:200]}")
        print(f"\nLast 200 chars of JSON block:\n{json_text[-200:]}")

        # Try to find syntax errors
        print("\nTrying to find syntax issues...")
        import json.decoder as decoder
        try:
            decoder.JSONDecoder().decode(json_text)
        except json.JSONDecodeError as err:
            print(f"Error at position {err.pos}: {err.msg}")
            print(f"Context: {json_text[max(0, err.pos-50):err.pos+50]}")
else:
    print("\n✗ No JSON code block found")

# Method 3: Find JSON object by brace matching
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
                print(f"\n✓ Method 3 (Brace matching): Found JSON object ({len(json_text)} chars)")
                try:
                    result = json.loads(json_text)
                    print(f"✓ SUCCESS")
                    print(f"Files found: {len(result.get('files', []))}")
                    for f in result.get('files', [])[:3]:
                        print(f"  - {f.get('path')}: {len(f.get('content', ''))} chars")
                except json.JSONDecodeError as e:
                    print(f"✗ FAILED - {e}")
                break
