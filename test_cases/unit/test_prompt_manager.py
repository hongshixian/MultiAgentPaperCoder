"""Unit tests for prompt manager."""

import pytest
from src.prompts import PROMPTS


class TestPromptManager:
    """Test cases for PromptManager class."""

    def test_manager_loads_templates(self):
        """Test that prompt manager loads templates from YAML files."""
        template_names = PROMPTS.get_template_names()
        assert len(template_names) > 0
        assert 'algorithm_analyzer' in template_names
        assert 'code_planner' in template_names
        assert 'code_generator' in template_names
        assert 'result_verification' in template_names
        assert 'error_repair' in template_names

    def test_get_template(self):
        """Test retrieving a template by name."""
        template = PROMPTS.get_template('algorithm_analyzer')
        assert template.name == 'algorithm_analyzer'
        assert template.template is not None
        assert isinstance(template.input_variables, list)

    def test_get_template_raises_keyerror(self):
        """Test that getting non-existent template raises KeyError."""
        with pytest.raises(KeyError, match="Prompt template 'nonexistent' not found"):
            PROMPTS.get_template('nonexistent')

    def test_format_template(self):
        """Test formatting a template with variables."""
        result = PROMPTS.format_template(
            'algorithm_analyzer',
            paper_content='Test content',
            title='Test Title',
            abstract='Test abstract'
        )
        assert 'Test content' in result
        assert 'Test Title' in result

    def test_format_template_missing_variable(self):
        """Test that formatting with missing variables raises ValueError."""
        with pytest.raises(ValueError, match="Missing required variables"):
            PROMPTS.format_template('algorithm_analyzer', paper_content='Test')

    def test_get_system_prompt(self):
        """Test getting system prompt from template."""
        system_prompt = PROMPTS.get_system_prompt('algorithm_analyzer')
        assert isinstance(system_prompt, str)
        assert 'machine learning' in system_prompt.lower()

    def test_get_system_prompt_nonexistent(self):
        """Test getting system prompt for non-existent template raises KeyError."""
        with pytest.raises(KeyError):
            PROMPTS.get_system_prompt('nonexistent')
