"""Main entry point for MultiAgentPaperCoder."""

import os
import sys
import argparse
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def check_environment():
    """Check if required environment variables are set."""
    llm_provider = os.getenv("LLM_PROVIDER", "claude")

    if llm_provider == "zhipu":
        api_key = os.getenv("ZHIPU_API_KEY")
        if not api_key:
            print("Error: ZHIPU_API_KEY not set in .env file or environment")
            print("Please set it in .env file:")
            print("  ZHIPU_API_KEY=your_zhipu_api_key_here")
            return False
    else:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("Error: ANTHROPIC_API_KEY not set in .env file or environment")
            print("Please set it in .env file:")
            print("  ANTHROPIC_API_KEY=your_api_key_here")
            return False

    return True


def check_conda_env(env_name="py12pt"):
    """Check if conda environment exists."""
    try:
        import subprocess
        result = subprocess.run(
            ["conda", "env", "list", "--json"],
            capture_output=True,
            timeout=10,
        )
        if result.returncode == 0:
            envs = json.loads(result.stdout.decode())
            env_names = [Path(env).name for env in envs["envs"]]
            return env_name in env_names
    except Exception:
        pass
    return None  # Could not determine


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="MultiAgentPaperCoder - Automatically reproduce paper code"
    )
    parser.add_argument(
        "--pdf",
        type=str,
        required=True,
        help="Path to PDF paper file"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./output/generated_code",
        help="Output directory for generated code (default: ./output/generated_code)"
    )
    parser.add_argument(
        "--conda-env",
        type=str,
        default="py12pt",
        help="Conda environment name (default: py12pt)"
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip code validation step"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    # Check environment
    print("Checking environment...")
    if not check_environment():
        sys.exit(1)

    # Check conda environment
    print(f"Checking conda environment '{args.conda_env}'...")
    conda_exists = check_conda_env(args.conda_env)
    if conda_exists is False:
        print(f"Warning: Conda environment '{args.conda_env}' not found")
        print("The code validation step may fail if the environment is not available")
        print(f"Create it with: conda create -n {args.conda_env} python=3.12")
    elif conda_exists is True:
        print(f"✓ Conda environment '{args.conda_env}' found")

    # Check PDF file
    if not os.path.exists(args.pdf):
        print(f"Error: PDF file not found: {args.pdf}")
        sys.exit(1)

    print(f"✓ PDF file found: {args.pdf}")

    # Create output directory
    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    print(f"✓ Output directory: {output_dir}")

    # Initialize and run workflow
    print("\n" + "=" * 60)
    print("Starting MultiAgentPaperCoder")
    print("=" * 60)

    try:
        from src.graph.workflow import PaperCoderWorkflow

        config = {
            "output_dir": output_dir,
            "conda_env_name": args.conda_env,
            "verbose": args.verbose,
            "skip_validation": args.skip_validation,
        }

        workflow = PaperCoderWorkflow(config)
        state = workflow.run(args.pdf)

        # Print summary
        summary = workflow.get_summary(state)
        print("\n" + summary)

        # Exit with appropriate code
        if state.get("status") == "success":
            print("\n🎉 Paper code successfully reproduced!")
            sys.exit(0)
        else:
            print(f"\n⚠ Process completed with status: {state.get('status', 'unknown')}")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
