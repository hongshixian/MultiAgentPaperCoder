"""Configuration management for MultiAgentPaperCoder.

This module provides a centralized configuration system using Pydantic
for type-safe configuration from multiple sources (defaults, .env, CLI args, YAML files).
"""

import os
from pathlib import Path
from typing import Optional, Literal
from datetime import datetime

try:
    from pydantic import BaseSettings, Field, field_validator
    from pydantic_settings import BaseSettings, YamlConfigSettingsSource, SettingsConfigDict
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseSettings = object  # Fallback

from dotenv import load_dotenv

load_dotenv()


class AppConfig:
    """Application configuration for MultiAgentPaperCoder.

    This class provides centralized configuration with type validation
    and loading from multiple sources in priority order:
    1. Environment variables
    2. .env file
    3. YAML config file
    4. CLI arguments
    5. Default values
    """

    def __init__(
        self,
        # LLM Configuration
        llm_provider: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        claude_model: Optional[str] = None,
        zhipu_api_key: Optional[str] = None,
        zhipu_model: Optional[str] = None,
        zhipu_base_url: Optional[str] = None,
        llm_max_tokens: Optional[int] = None,
        llm_temperature: Optional[float] = None,
        timeout_seconds: Optional[int] = None,

        # Execution Configuration
        conda_env_name: Optional[str] = None,
        default_output_dir: Optional[Path] = None,
        max_retries: Optional[int] = None,
        skip_validation: Optional[bool] = None,
        verbose: Optional[bool] = None,

        # Derived configuration
        current_output_dir: Optional[Path] = None,
    ):
        # LLM Configuration
        self.llm_provider = llm_provider or os.getenv("LLM_PROVIDER", "zhipu")
        self.anthropic_api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.claude_model = claude_model or os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
        self.zhipu_api_key = zhipu_api_key or os.getenv("ZHIPU_API_KEY", "")
        self.zhipu_model = zhipu_model or os.getenv("ZHIPU_MODEL", "glm-5")
        self.zhipu_base_url = zhipu_base_url or os.getenv(
            "ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"
        )
        self.llm_max_tokens = llm_max_tokens or int(os.getenv("LLM_MAX_TOKENS", "4096"))
        self.llm_temperature = llm_temperature or float(os.getenv("LLM_TEMPERATURE", "0.7"))
        self.timeout_seconds = timeout_seconds or int(os.getenv("TIMEOUT_SECONDS", "300"))

        # Execution Configuration
        self.conda_env_name = conda_env_name or os.getenv("CONDA_ENV_NAME", "py12pt")
        self.default_output_dir = default_output_dir or Path(
            os.getenv("OUTPUT_DIR", "./output")
        )
        self.max_retries = max_retries or int(os.getenv("MAX_RETRIES", "3"))
        self.skip_validation = skip_validation or os.getenv("ENABLE_CACHE", "false").lower() == "true"
        self.verbose = verbose or os.getenv("LOG_LEVEL", "INFO") == "DEBUG"

        # Derived configuration
        self.current_output_dir = current_output_dir

    def validate(self) -> list:
        """Validate configuration and return list of errors.

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # Validate LLM provider
        if self.llm_provider not in ["claude", "zhipu"]:
            errors.append(
                f"Invalid LLM provider: {self.llm_provider}. "
                f"Must be 'claude' or 'zhipu'"
            )

        # Validate API keys based on provider
        if self.llm_provider == "zhipu":
            if not self.zhipu_api_key:
                errors.append(
                    "ZHIPU_API_KEY not set. "
                    "Please set it in .env file or environment variable."
                )
        else:  # claude
            if not self.anthropic_api_key:
                errors.append(
                    "ANTHROPIC_API_KEY not set. "
                    "Please set it in .env file or environment variable."
                )

        # Validate output directory
        try:
            if not self.default_output_dir.exists():
                self.default_output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create output directory: {e}")

        return errors

    def generate_output_path(
        self, pdf_path: Path, base_dir: Optional[Path] = None, timestamp: Optional[datetime] = None
    ) -> Path:
        """Generate unique output path based on PDF filename and timestamp.

        Args:
            pdf_path: Path to the PDF file
            base_dir: Base output directory (uses default if None)
            timestamp: Timestamp to use (uses current time if None)

        Returns:
            Path object for the unique output directory
        """
        if base_dir is None:
            base_dir = self.default_output_dir

        if timestamp is None:
            timestamp = datetime.now()

        # Extract PDF filename without extension
        pdf_name = Path(pdf_path).stem

        # Create timestamp string
        time_str = timestamp.strftime("%Y%m%d_%H%M%S")

        # Combine timestamp and PDF name
        output_name = f"{time_str}_{pdf_name}"

        # Create full path
        return base_dir / output_name

    @classmethod
    def from_cli_args(cls, args) -> "AppConfig":
        """Create configuration from CLI arguments.

        Args:
            args: Parsed CLI arguments (argparse.Namespace)

        Returns:
            AppConfig instance
        """
        # Extract attributes from args if they exist
        kwargs = {}

        # Check for common CLI argument names
        for attr in ["pdf", "config", "conda_env", "output_dir", "verbose", "skip_validation"]:
            if hasattr(args, attr):
                value = getattr(args, attr)
                if value is not None:
                    kwargs[attr] = value

        return cls(**kwargs)

    @classmethod
    def from_yaml(cls, config_path: Path) -> "AppConfig":
        """Create configuration from YAML file.

        Args:
            config_path: Path to YAML configuration file

        Returns:
            AppConfig instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML is invalid
        """
        try:
            import yaml
        except ImportError:
            raise ImportError(
                "PyYAML not installed. "
                "Install it with: pip install pyyaml"
            )

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)

        return cls(**config_dict)

    def get_api_key(self) -> str:
        """Get the appropriate API key based on provider.

        Returns:
            API key string for current provider
        """
        if self.llm_provider == "zhipu":
            return self.zhipu_api_key
        else:
            return self.anthropic_api_key

    def get_model(self) -> str:
        """Get the model name for current provider.

        Returns:
            Model name string for current provider
        """
        if self.llm_provider == "zhipu":
            return self.zhipu_model
        else:
            return self.claude_model

    def __repr__(self) -> str:
        """Return string representation of configuration."""
        return (
            f"AppConfig("
            f"provider={self.llm_provider}, "
            f"model={self.get_model()}, "
            f"output_dir={self.default_output_dir}, "
            f"conda_env={self.conda_env_name})"
        )


def create_default_config() -> AppConfig:
    """Create configuration with default values.

    Returns:
        AppConfig instance with all default values
    """
    return AppConfig()


def load_config_from_file(config_path: Optional[Path] = None) -> AppConfig:
    """Load configuration from file or use defaults.

    Args:
        config_path: Optional path to YAML config file

    Returns:
        AppConfig instance
    """
    if config_path and config_path.exists():
        return AppConfig.from_yaml(config_path)
    return create_default_config()
