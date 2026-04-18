"""Unit tests for LLM client."""

import pytest
from src.llms.llm_client import LLMClient


class TestLLMClientJSONParsing:
    """Test cases for LLMClient JSON parsing methods."""

    def test_parse_json_direct(self):
        """Test parsing valid JSON directly."""
        result = LLMClient._parse_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_json_from_code_block(self):
        """Test parsing JSON from markdown code block."""
        response = '''```json
        {"name": "test", "value": 42}
        ```'''
        result = LLMClient._parse_json(response)
        assert result == {"name": "test", "value": 42}

    def test_parse_json_from_code_block_no_json_label(self):
        """Test parsing JSON from code block without json label."""
        response = '''```
        {"name": "test", "value": 42}
        ```'''
        result = LLMClient._parse_json(response)
        assert result == {"name": "test", "value": 42}

    def test_parse_json_with_trailing_comma(self):
        """Test parsing JSON with trailing commas."""
        response = '{"key": "value", "number": 42,}'
        result = LLMClient._parse_json(response)
        assert result == {"key": "value", "number": 42}

    def test_parse_json_with_line_comments(self):
        """Test parsing JSON with line comments."""
        response = '{\n  "key": "value",\n  // comment\n  "number": 42\n}'
        result = LLMClient._parse_json(response)
        assert result == {"key": "value", "number": 42}

    def test_parse_json_finds_first_balanced_braces(self):
        """Test that parser finds first balanced {} pair."""
        response = 'Some text {"key": "value"} more text {"another": "pair"}'
        result = LLMClient._parse_json(response)
        assert result == {"key": "value"}

    def test_parse_json_invalid_raises_error(self):
        """Test that invalid JSON raises ValueError."""
        with pytest.raises(ValueError, match="Failed to parse LLM response as JSON"):
            LLMClient._parse_json('not valid json at all')

    def test_parse_robust_with_trailing_comma(self):
        """Test _parse_robust handles trailing comma."""
        result = LLMClient._parse_robust('{"key": "value",}')
        assert result == {"key": "value"}


class TestGetLLMFactory:
    """Test cases for get_llm factory function."""

    def test_get_llm_zhipu(self):
        """Test creating Zhipu LLM."""
        llm = LLMClient.get_llm(
            provider='zhipu',
            model='glm-4',
            api_key='test_key'
        )
        assert llm is not None
        assert llm.model_name == 'glm-4'

    def test_get_llm_claude(self):
        """Test creating Claude LLM."""
        llm = LLMClient.get_llm(
            provider='claude',
            model='claude-3',
            api_key='test_key'
        )
        assert llm is not None
        assert llm.model_name == 'claude-3'
