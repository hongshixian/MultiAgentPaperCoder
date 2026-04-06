"""Test with real PDF file."""

import os
import sys

# Set environment variables for ZhipuAI
os.environ["LLM_PROVIDER"] = "zhipu"
os.environ["ZHIPU_API_KEY"] = "ee224389b92c47289d801c3b5674aa1e.RxOdScSDxcZwO0vi"
os.environ["ZHIPU_MODEL"] = "glm-5"
os.environ["ZHIPU_BASE_URL"] = "https://open.bigmodel.cn/api/paas/v4"

# Set other config
os.environ["LLM_MAX_TOKENS"] = "4096"
os.environ["LLM_TEMPERATURE"] = "0.7"
os.environ["OUTPUT_DIR"] = "./output/generated_code"
os.environ["CONDA_ENV_NAME"] = "py12pt"

# Add src to path
sys.path.insert(0, "src")

from src.graph.workflow import PaperCoderWorkflow


def main():
    """Run workflow with PDF."""
    print("=" * 60)
    print("Testing with Real PDF File")
    print("=" * 60)

    pdf_path = "paper_examples/1607.01759v3.pdf"

    if not os.path.exists(pdf_path):
        print(f"Error: PDF not found: {pdf_path}")
        return 1

    print(f"\nPDF: {pdf_path}")
    print(f"Size: {os.path.getsize(pdf_path)} bytes")

    # Create workflow
    config = {
        "output_dir": "./output/generated_code",
        "conda_env_name": "py12pt",
        "skip_validation": True,  # Skip validation for testing
        "max_retries": 2,
    }

    try:
        print("\nStarting workflow...")
        print("This may take several minutes...\n")

        workflow = PaperCoderWorkflow(config)
        state = workflow.run(pdf_path)

        # Print summary
        summary = workflow.get_summary(state)
        print("\n" + summary)

        return 0 if state.get("status") == "success" else 1

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
