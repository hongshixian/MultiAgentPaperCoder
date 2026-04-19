"""Configuration for the DeepAgents-based paper reproduction app."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    """Runtime settings for the DeepAgents implementation."""

    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_base_url: str = field(default_factory=lambda: os.getenv("OPENAI_BASE_URL", "").strip())
    model_name: str = field(default_factory=lambda: os.getenv("MODEL_NAME", "gpt-5.4"))
    output_root: Path = field(
        default_factory=lambda: _resolve_output_root(
            os.getenv("OUTPUT_ROOT"),
            os.getenv("OUTPUT_DIR"),
        )
    )
    log_dir_override: str = field(default_factory=lambda: os.getenv("LOG_DIR", "").strip())

    @property
    def artifacts_dir(self) -> Path:
        return self.output_root / "artifacts"

    @property
    def generated_code_dir(self) -> Path:
        return self.output_root / "generated_code"

    @property
    def paper_analysis_path(self) -> Path:
        return self.artifacts_dir / "paper_analysis.txt"

    @property
    def verification_report_path(self) -> Path:
        return self.artifacts_dir / "verification_report.txt"

    @property
    def log_dir(self) -> Path:
        if self.log_dir_override:
            return Path(self.log_dir_override)
        return self.output_root / "logs"

    def ensure_dirs(self) -> None:
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.generated_code_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    @property
    def resolved_model_name(self) -> str:
        """Normalize provider-prefixed model names to raw OpenAI-compatible names."""
        if ":" in self.model_name:
            _, model = self.model_name.split(":", 1)
            return model
        return self.model_name

    def build_llm(self):
        """Build an OpenAI-compatible LangChain chat model."""
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise ImportError(
                "langchain-openai is not installed. Install project requirements before building the agent."
            ) from exc

        kwargs = {
            "model": self.resolved_model_name,
            "api_key": self.openai_api_key,
        }
        if self.openai_base_url:
            kwargs["base_url"] = self.openai_base_url
        return ChatOpenAI(**kwargs)

    def create_run_output_root(self, pdf_path: Path, timestamp: datetime | None = None) -> Path:
        """Create a unique output directory for a single run."""
        timestamp = timestamp or datetime.now()
        slug = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{pdf_path.stem}"
        return self.output_root / slug


def _resolve_output_root(output_root: str | None, output_dir: str | None) -> Path:
    """Resolve output root from modern or legacy-style output settings."""
    if output_root:
        return Path(output_root)

    if output_dir:
        path = Path(output_dir)
        if path.name == "generated_code":
            return path.parent
        return path

    return Path("./output")
