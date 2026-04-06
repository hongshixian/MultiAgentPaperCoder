"""Simple test script to verify basic functionality."""

import os
import sys


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


def test_pdf_parser():
    """Test PDF parser with a simple test file."""
    print("\nTesting PDF parser...")

    from src.tools.pdf_parser import PDFParser

    parser = PDFParser()

    # Create a simple test PDF (optional)
    # For now, just check if parser is initialized
    print("✓ PDF parser initialized")
    return True


def test_workflow_creation():
    """Test workflow creation."""
    print("\nTesting workflow creation...")

    from src.graph.workflow import PaperCoderWorkflow

    try:
        workflow = PaperCoderWorkflow({
            "output_dir": "./test_output",
            "conda_env_name": "py12pt",
        })
        print("✓ Workflow created successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to create workflow: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("MultiAgentPaperCoder Test Suite")
    print("=" * 60)
    print()

    tests = [
        ("Import Test", test_imports),
        ("PDF Parser Test", test_pdf_parser),
        ("Workflow Creation Test", test_workflow_creation),
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
        icon = "✓与其他结果" if result else "✗"
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
