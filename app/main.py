"""CLI entrypoint for the DeepAgents paper reproduction app."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.agent import build_agent
from app.config import Settings


def build_user_prompt(pdf_path: str, output_dir: str) -> str:
    """Build the high-level paper reproduction task prompt."""
    return f"""
Run one paper reproduction workflow with these requirements:

1. Read the PDF at: {pdf_path}
2. Use the document-analyst subagent first and save the analysis under {output_dir}/artifacts/
3. Use the code-generator subagent to create a minimal Python project under {output_dir}/generated_code/
4. The generated project must include at least:
   - main.py
   - requirements.txt
5. Use the code-verifier subagent to verify the generated project
6. If verification fails, use the error-repairer subagent and then verify again
7. Final response must include:
   - paper method summary
   - generated files
   - verification status
   - unresolved issues and risks
"""


def main() -> None:
    """Parse CLI args and invoke the DeepAgents workflow."""
    parser = argparse.ArgumentParser(description="DeepAgents-based paper reproduction tool")
    parser.add_argument("--pdf", required=True, help="Path to the paper PDF")
    parser.add_argument("--output-dir", default="./output", help="Output directory root")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    settings = Settings(output_root=Path(args.output_dir))
    agent = build_agent(settings)

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": build_user_prompt(str(pdf_path), str(settings.output_root)),
                }
            ]
        }
    )
    print(result)


if __name__ == "__main__":
    main()
