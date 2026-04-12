#!/usr/bin/env python3
"""Test script to debug message flow between agents."""

import os
import sys
import json
from dotenv import load_dotenv

load_dotenv()

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.agents.pdf_reader import PDFReaderAgent
from src.agents.algorithm_analyzer import AlgorithmAnalyzerAgent
from src.agents.code_planner import CodePlannerAgent
from src.agents.code_generator import CodeGeneratorAgent


def print_state(state, title):
    """Print state information."""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

    # Print PDF path
    if "pdf_path" in state:
        print(f"✓ PDF path: {state['pdf_path']}")

    # Print paper content
    if "paper_content" in state and state["paper_content"]:
        paper = state["paper_content"]
        print(f"\n📄 Paper Content:")
        print(f"  - Title: {paper.get('title', 'N/A')}")
        print(f"  - Abstract length: {len(paper.get('abstract', ''))} chars")
        print(f"  - Full text length: {len(paper.get('full_text', ''))} chars")
        print(f"  - Sections: {len(paper.get('sections', []))}")
        print(f"  - First 200 chars of full text:")
        full_text = paper.get('full_text', '')[:200]
        print(f"    {full_text}")

    # Print Algorithm Analysis
    if "algorithm_analysis" in state and state["algorithm_analysis"]:
        algo = state["algorithm_analysis"]
        print(f"\n🧠 Algorithm Analysis:")
        print(f"  - Name: {algo.get('algorithm_name', 'N/A')}")
        print(f"  - Type: {algo.get('algorithm_type', 'N/A')}")
        print(f"  - Core Logic length: {len(algo.get('core_logic', ''))} chars")
        print(f"  - Pseudocode length: {len(algo.get('pseudocode', ''))} chars")
        print(f"  - Hyperparameters: {algo.get('hyperparameters', {})}")
        print(f"  - Requirements: {algo.get('requirements', {})}")
        print(f"  - First 200 chars of core logic:")
        core_logic = algo.get('core_logic', '')[:200]
        print(f"    {core_logic}")

    # Print Code Plan
    if "code_plan" in state and state["code_plan"]:
        plan = state["code_plan"]
        print(f"\n📋 Code Plan:")
        print(f"  - Project structure: {len(plan.get('project_structure', []))} files")
        print(f"  - Implementation steps: {len(plan.get('implementation_steps', []))} steps")
        print(f"  - Dependencies: {plan.get('dependencies', {})}")
        print(f"  - Entry points: {plan.get('entry_points', [])}")
        print(f"  - Test plan length: {len(plan.get('test_plan', ''))} chars")
        if plan.get('project_structure'):
            print(f"  - Files:")
            for file in plan['project_structure'][:5]:  # Show first 5
                print(f"    - {file.get('path', 'N/A')}: {file.get('description', 'N/A')}")

    # Print Generated Code
    if "generated_code" in state and state["generated_code"]:
        code = state["generated_code"]
        print(f"\n💻 Generated Code:")
        print(f"  - Files: {code.get('total_files', 0)}")
        print(f"  - Directory: {code.get('code_dir', 'N/A')}")
        print(f"  - Summary: {code.get('summary', 'N/A')[:200]}")

    # Print Errors
    if "errors" in state and state["errors"]:
        print(f"\n❌ Errors:")
        for error in state["errors"]:
            print(f"  - {error}")

    # Print Current Step
    if "current_step" in state:
        print(f"\n📍 Current Step: {state['current_step']}")


def main():
    """Test message flow."""
    pdf_path = "/home/lihao/git/MultiAgentPaperCoder/paper_examples/1607.01759v3.pdf"

    # Check if PDF exists
    if not os.path.exists(pdf_path):
        print(f"Error: PDF not found: {pdf_path}")
        return 1

    # Initialize agents
    print("Initializing agents...")
    config = {
        "output_dir": "/tmp/test_debug_output",
        "conda_env_name": "py12pt",
    }

    pdf_reader = PDFReaderAgent(config)
    algorithm_analyzer = AlgorithmAnalyzerAgent(config)
    code_planner = CodePlannerAgent(config)
    code_generator = CodeGeneratorAgent(config)

    # Initial state
    state = {
        "pdf_path": pdf_path,
        "paper_content": None,
        "algorithm_analysis": None,
        "code_plan": None,
        "generated_code": None,
        "current_step": "start",
        "errors": [],
        "retry_count": 0,
        "max_retries": 3,
    }

    print_state(state, "Initial State")

    # Step 1: PDF Reading
    print("\n🔍 Step 1: PDF Reading")
    state = pdf_reader(state)
    print_state(state, "After PDF Reader")

    if state.get("errors"):
        print("\n❌ Errors detected, stopping.")
        return 1

    # Step 2: Algorithm Analysis
    print("\n🔍 Step 2: Algorithm Analysis")
    state = algorithm_analyzer(state)
    print_state(state, "After Algorithm Analyzer")

    if state.get("errors"):
        print("\n❌ Errors detected, stopping.")
        return 1

    # Step 3: Code Planning
    print("\n🔍 Step 3: Code Planning")
    state = code_planner(state)
    print_state(state, "After Code Planner")

    if state.get("errors"):
        print("\n❌ Errors detected, stopping.")
        return 1

    # Step 4: Code Generation
    print("\n🔍 Step 4: Code Generation")
    state = code_generator(state)
    print_state(state, "After Code Generator")

    if state.get("errors"):
        print("\n❌ Errors detected.")
        return 1

    print("\n✅ Message flow test completed successfully!")

    # Save full state for inspection
    output_file = "/tmp/test_debug_output/full_state.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Create a copy of state with serializable content
    serializable_state = {}
    for key, value in state.items():
        if isinstance(value, dict):
            serializable_state[key] = value
        elif isinstance(value, list):
            serializable_state[key] = value
        elif isinstance(value, (str, int, float, bool)):
            serializable_state[key] = value
        else:
            serializable_state[key] = str(value)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(serializable_state, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Full state saved to: {output_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
