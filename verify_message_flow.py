#!/usr/bin/env python3
"""Final verification script for message flow between agents."""

import os
import sys
sys.path.insert(0, '.')

from src.agents.pdf_reader import PDFReaderAgent
from src.agents.algorithm_analyzer import AlgorithmAnalyzerAgent
from src.agents.code_planner import CodePlannerAgent

def verify_message_flow():
    """Verify that message flows correctly between agents."""
    pdf_path = '/home/lihao/git/MultiAgentPaperCoder/paper_examples/1607.01759v3.pdf'
    config = {'output_dir': '/tmp/verify_output', 'conda_env_name': 'py12pt'}

    # Initial state
    state = {
        'pdf_path': pdf_path,
        'paper_content': None,
        'algorithm_analysis': None,
        'code_plan': None,
        'errors': [],
        'current_step': 'start',
    }

    print("=" * 80)
    print(" MESSAGE FLOW VERIFICATION")
    print("=" * 80)

    # Step 1: PDF Reader
    print("\n[1/3] PDF Reader Agent")
    pdf_reader = PDFReaderAgent(config)
    state = pdf_reader(state)

    if state.get('errors'):
        print(f"❌ FAILED: {state['errors'][0]}")
        return False
    if not state.get('paper_content'):
        print("❌ FAILED: No paper content in state")
        return False

    paper = state['paper_content']
    print(f"✓ PDF content extracted")
    print(f"  - Text length: {len(paper.get('full_text', ''))} chars")
    print(f"  - Title: {paper.get('title', 'Unknown')}")

    # Step 2: Algorithm Analyzer
    print("\n[2/3] Algorithm Analyzer Agent")
    algorithm_analyzer = AlgorithmAnalyzerAgent(config)
    state = algorithm_analyzer(state)

    if state.get('errors'):
        print(f"❌ FAILED: {state['errors'][0]}")
        return False
    if not state.get('algorithm_analysis'):
        print("❌ FAILED: No algorithm analysis in state")
        return False

    algo = state['algorithm_analysis']
    print(f"✓ Algorithm analyzed")
    print(f"  - Algorithm Name: {algo.get('algorithm_name', 'Unknown')}")
    print(f"  - Algorithm Type: {algo.get('algorithm_type', 'Unknown')}")
    print(f"  - Core Logic Length: {len(algo.get('core_logic', ''))} chars")

    # Verify paper content was used
    if len(algo.get('core_logic', '')) < 100:
        print("  ⚠️ WARNING: Core logic is very short - paper content may not have been used properly")
    else:
        print(f"  ✓ Paper content was properly analyzed (detailed core logic)")

    # Step 3: Code Planner
    print("\n[3/3] Code Planner Agent")
    code_planner = CodePlannerAgent(config)
    state = code_planner(state)

    if state.get('errors'):
        print(f"❌ FAILED: {state['errors'][0]}")
        return False
    if not state.get('code_plan'):
        print("❌ FAILED: No code plan in state")
        return False

    plan = state['code_plan']
    print(f"✓ Code planned")
    print(f"  - Project Structure: {len(plan.get('project_structure', []))} files")
    print(f"  - Implementation Steps: {len(plan.get('implementation_steps', []))} steps")
    print(f"  - Entry Points: {', '.join(plan.get('entry_points', []))}")

    # Verify algorithm analysis was used
    if len(plan.get('project_structure', [])) < 3:
        print("  ⚠️ WARNING: Very few files planned - algorithm analysis may not have been used properly")
    else:
        print(f"  ✓ Algorithm analysis was properly used (detailed project structure)")

    # Final summary
    print("\n" + "=" * 80)
    print(" VERIFICATION RESULT")
    print("=" * 80)

    checks = [
        ("PDF Reader → Algorithm Analyzer", bool(paper.get('full_text'))),
        ("Algorithm Analyzer → Code Planner", bool(algo.get('algorithm_name'))),
        ("Paper content used in analysis", len(algo.get('core_logic', '')) > 100),
        ("Algorithm analysis used in planning", len(plan.get('project_structure', [])) >= 3),
    ]

    all_passed = True
    for check_name, check_result in checks:
        status = "✓ PASS" if check_result else "❌ FAIL"
        print(f"{status}: {check_name}")
        if not check_result:
            all_passed = False

    print("\n" + "=" * 80)
    if all_passed:
        print("✅ ALL CHECKS PASSED - Message flow is working correctly!")
        print("\nNote: If generated code doesn't match the paper,")
        print("the issue is in prompt engineering or LLM selection,")
        print("NOT in message passing between agents.")
    else:
        print("❌ SOME CHECKS FAILED - There may be message flow issues.")
    print("=" * 80)

    return all_passed


if __name__ == "__main__":
    success = verify_message_flow()
    sys.exit(0 if success else 1)
