"""Test code generation specifically."""

import os
import sys

os.environ["LLM_PROVIDER"] = "zhipu"
os.environ["ZHIPU_API_KEY"] = "ee224389b92c47289d801c3b5674aa1e.RxOdScSDxcZwO0vi"
os.environ["ZHIPU_MODEL"] = "glm-5"
os.environ["ZHIPU_BASE_URL"] = "https://open.bigmodel.cn/api/paas/v4"

sys.path.insert(0, "src")

from src.agents.code_generator import CodeGeneratorAgent


def main():
    """Test code generation."""
    print("=" * 60)
    print("Testing Code Generation with ZhipuAI")
    print("=" * 60)

    # Create generator
    generator = CodeGeneratorAgent({
        "output_dir": "./test_gen_output",
    })

    # Create state with algorithm analysis and code plan
    state = {
        "pdf_path": "test.pdf",
        "paper_content": {},
        "algorithm_analysis": {
            "algorithm_name": "Simple Linear Regression",
            "algorithm_type": "regression",
            "core_logic": "Minimizes MSE loss using gradient descent",
            "pseudocode": "Initialize w, b. Iterate: pred = w*x+b. Update: w -= lr*dw.",
            "hyperparameters": {
                "learning_rate": "0.01",
                "max_iterations": "1000",
            },
            "requirements": {
                "dataset": "Numerical data",
                "frameworks": ["numpy"],
                "compute": "CPU",
            },
            "data_flow": "Input -> Model -> Output",
        },
        "code_plan": {
            "project_structure": [
                {
                    "path": "main.py",
                    "description": "Main training script",
                    "type": "script",
                },
                {
                    "path": "model.py",
                    "description": "Model definition",
                    "type": "module",
                },
                {
                    "path": "config.py",
                    "description": "Configuration file",
                    "type": "module",
                },
            ],
            "implementation_steps": [
                "Step 1: Create config.py with hyperparameters",
                "Step 2: Implement LinearRegression class",
                "Step 3: Create main.py with training loop",
            ],
            "dependencies": {
                "python_packages": ["numpy>=1.21.0"],
                "system_packages": [],
            },
            "entry_points": ["main.py"],
            "test_plan": "Test with synthetic data",
        },
        "current_step": "code_planning_completed",
        "errors": [],
    }

    print("\nAlgorithm analysis:")
    print(f"  Name: {state['algorithm_analysis']['algorithm_name']}")
    print(f"  Type: {state['algorithm_analysis']['algorithm_type']}")

    print("\nCode plan:")
    print(f"  Files to generate: {len(state['code_plan']['project_structure'])}")
    print(f"  Implementation steps: {len(state['code_plan']['implementation_steps'])}")

    print("\nGenerating code...")
    print("(This may take a minute or two...)\n")

    try:
        result = generator(state)

        if result.get("errors"):
            print("\n✗ Code generation failed:")
            for error in result["errors"]:
                print(f"  - {error}")
            return 1

        if result.get("generated_code"):
            code = result["generated_code"]
            print("\n✓ Code generation successful!")
            print(f"  Files generated: {code.get('total_files', 0)}")
            print(f"  Output directory: {code.get('code_dir', 'Unknown')}")

            if code.get("file_paths"):
                print("\nGenerated files:")
                for file_path in code["file_paths"]:
                    print(f"  - {file_path}")

            return 0
        else:
            print("\n✗ No generated code in result")
            return 1

    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
