"""Simple test script to verify basic functionality."""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def test_imports():
    """Test if all modules can be imported."""
    print("Testing imports...")

    try:
        from src.state import PaperState
        print("✓ State module imported")
    except Exception as e:
        print(f"✗ Failed to import state: {e}")
        return False

    try:
        from src.tools import LLMClient, PDFParser, CodeExecutor
        print("✓ Tools module imported")
    except Exception as e:
        print(f"✗ Failed to import tools: {e}")
        return False

    try:
        from src.agents import (
            BaseAgent,
            PDFReaderAgent,
            AlgorithmAnalyzerAgent,
            CodePlannerAgent,
            CodeGeneratorAgent,
            CodeValidatorAgent,
        )
        print("✓ Agents module imported")
    except Exception as e:
        print(f"✗ Failed to import agents: {e}")
        return False

    try:
        from src.graph import PaperCoderWorkflow
        print("✓ Graph module imported")
    except Exception as e:
        print(f"✗ Failed to import graph: {e}")
        return False

    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("MultiAgentPaperCoder Test Suite")
    print("=" * 60)
    print()

    tests = [
        ("Import Test", test_imports),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ Test crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        icon = "✓" if result else "✗"
        print(f"{icon} {test_name}")

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
