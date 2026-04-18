"""Main entry point for MultiAgentPaperCoder."""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


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
        "--config",
        type=str,
        help="Path to configuration file (default: config/default.yaml)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    # Load configuration from .env
    from src.config import AppConfig

    config = AppConfig()

    # Override with CLI arguments
    config.verbose = args.verbose

    # Validate configuration
    print("\nValidating configuration...")
    errors = config.validate()
    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    print("✓ Configuration is valid")

    # Check PDF file
    if not os.path.exists(args.pdf):
        print(f"Error: PDF file not found: {args.pdf}")
        sys.exit(1)

    print(f"✓ PDF file found: {args.pdf}")

    # Generate unique output path based on PDF and timestamp
    pdf_path = Path(args.pdf)
    output_dir = config.generate_output_path(pdf_path)
    config.current_output_dir = output_dir

    print(f"✓ Output directory: {output_dir}")
    print(f"  LLM Provider: {config.llm_provider}")
    print(f"  LLM Model: {config.get_model()}")
    print(f"  Conda Environment: {config.conda_env}")

    # Initialize and run workflow
    print("\n" + "=" * 60)
    print("Starting MultiAgentPaperCoder")
    print("=" * 60)

    try:
        from src.graph.workflow import PaperCoderWorkflow

        # Convert config to dict for workflow
        workflow_config = {
            "output_dir": str(config.current_output_dir),
            "conda_env_name": config.conda_env,
            "verbose": config.verbose,
            "skip_validation": config.skip_validation,
            "max_retries": config.max_retries,
            "llm_provider": config.llm_provider,
            "llm_max_tokens": config.llm_max_tokens,
            "llm_temperature": config.llm_temperature,
            "timeout_seconds": config.timeout_seconds,
        }

        workflow = PaperCoderWorkflow(workflow_config)
        state = workflow.run(str(args.pdf))

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
        if config.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
