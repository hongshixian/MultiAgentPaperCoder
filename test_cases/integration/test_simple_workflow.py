"""Simple workflow test without code generation."""

import os
import sys
import textwrap

# Set environment variables for ZhipuAI
os.environ["LLM_PROVIDER"] = "zhipu"
os.environ["ZHIPU_API_KEY"] = "ee224389b92c47289d801c3b5674aa1e.RxOdScSDxcZwO0vi"
os.environ["ZHIPU_MODEL"] = "glm-5"
os.environ["ZHIPU_BASE_URL"] = "https://open.bigmodel.cn/api/paas/v4"

sys.path.insert(0, "src")

from src.agents.algorithm_analyzer import AlgorithmAnalyzerAgent
from src.agents.code_planner import CodePlannerAgent


def test_workflow():
    """Test workflow without code generation."""
    print("=" * 60)
    print("Testing Multi-Agent Workflow (No Code Generation)")
    print("=" * 60)

    # Create agents
    analyzer = AlgorithmAnalyzerAgent()
    planner = CodePlannerAgent()

    # Initial state
    state = {
        "pdf_path": "test.pdf",
        "paper_content": {
            "title": "Simple Linear Regression",
            "abstract": "A simple linear regression algorithm using gradient descent.",
            "full_text": textwrap.dedent("""
            # Simple Linear Regression with Gradient

            ## Abstract
            This paper presents a simple linear regression
            algorithm using gradient descent optimization.

            ## Method
            Minimizes MSE loss with gradient descent.
            Parameters: w (weight), b (bias), lr=0.01.
            """),
            "sections": [],
            "formulas": [],
            "figures": [],
        },
        "current_step": "pdf_reading_completed",
        "errors": [],
    }

    # Step 1: Algorithm Analysis
    print("\n[Step 1] Algorithm Analysis...")
    state = analyzer(state)

    if state.get("errors"):
        print("Failed: " + str(state["errors"]))
        return False

    analysis = state.get("algorithm_analysis", {})
    print("Success!")
    print("  Algorithm: " + str(analysis.get("algorithm_name", "Unknown")))
    print("  Type: " + str(analysis.get("algorithm_type", "Unknown")))

    # Step 2: Code Planning
    print("\n[Step 2] Code Planning...")
    state = planner(state)

    if state.get("errors"):
        print("Failed: " + str(state["errors"]))
        return False

    plan = state.get("code_plan", {})
    print("Success!")
    print("  Files: " + str(len(plan.get("project_structure", []))))
    print("  Steps: " + str(len(plan.get("implementation_steps", []))))

    # Show some details
    print("\nProject Structure Preview:")
    for i, item in enumerate(plan.get("project_structure", [])[:3], 1):
        print("  " + str(i) + ". " + str(item.get("path", "")))

    print("\nImplementation Steps Preview:")
    for i, step in enumerate(plan.get("implementation_steps", [])[:3], 1):
        print("  " + str(i) + ". " + step)

    deps = plan.get("dependencies", {})
    print("\nDependencies:")
    print("  Python: " + ", ".join(deps.get("python_packages", [])[:3]))
    print("  Entry: " + str(plan.get("entry_points", [])))

    return True


def main():
    """Run test."""
    print("Multi-Agent Workflow Test")

    try:
        if test_workflow():
            print("\nSuccess! Workflow executed successfully.")
            return 0
        else:
            print("\nTest failed")
            return 1
    except Exception as e:
        print("Error: " + str(e))
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
