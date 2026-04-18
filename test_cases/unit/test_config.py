"""Unit tests for config module."""

import os
import pytest
from unittest.mock import patch

from src.config import AppConfig


class TestAppConfig:
    """Test cases for AppConfig class."""

    def test_config_loads_from_env(self):
        """Test that config loads from environment variables."""
        with patch.dict(os.environ, {
            'LLM_PROVIDER': 'zhipu',
            'ZHIPU_API_KEY': 'test_key',
            'CONDA_ENV_NAME': 'test_env',
            'OUTPUT_DIR': '/test/output',
        }):
            config = AppConfig()
            assert config.llm_provider == 'zhipu'
            assert config.conda_env_name == 'test_env'

    def test_config_defaults(self):
        """Test that config has sensible defaults."""
        with patch.dict(os.environ, {}, clear=True):
            config = AppConfig()
            assert config.llm_provider == 'zhipu'
            assert config.conda_env_name == 'py12pt'
            assert config.max_retries == 3

    def test_config_output_dir_generation(self):
        """Test that output directory is generated with timestamp."""
        with patch.dict(os.environ, {}, clear=True):
            config = AppConfig(pdf_name='test_paper.pdf')
            output_dir = config.get_output_dir()
            assert 'test_paper' in output_dir
            assert 'generated_code' in output_dir
