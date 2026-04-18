"""Integration tests for workflow."""

import pytest
from src.graph.workflow import create_workflow, _create_initial_state, should_continue_verification


class TestWorkflowCreation:
    """Test cases for workflow creation and structure."""

    def test_create_workflow(self):
        """Test that workflow can be created."""
        workflow = create_workflow()
        assert workflow is not None

    def test_create_initial_state(self):
        """Test initial state creation."""
        state = _create_initial_state('/test/paper.pdf')
        assert state['pdf_path'] == '/test/paper.pdf'
        assert state['iteration_count'] == 0
        assert state['max_iterations'] == 5
        assert state['errors'] == []


class TestConditionalRouting:
    """Test cases for conditional routing logic."""

    def test_should_continue_verification_end(self):
        """Test that workflow ends when verification passes."""
        state = {
            'verification_result': {
                'needs_repair': False,
                'needs_regeneration': False,
            },
            'iteration_count': 0,
            'max_iterations': 5,
        }
        result = should_continue_verification(state)
        assert result == "end"

    def test_should_continue_verification_repair(self):
        """Test that workflow goes to repair when needed."""
        state = {
            'verification_result': {
                'needs_repair': True,
                'needs_regeneration': False,
            },
            'iteration_count': 0,
            'max_iterations': 5,
        }
        result = should_continue_verification(state)
        assert result == "error_repair"

    def test_should_continue_verification_regeneration(self):
        """Test that workflow goes to regeneration when needed."""
        state = {
            'verification_result': {
                'needs_repair': False,
                'needs_regeneration': True,
            },
            'iteration_count': 0,
            'max_iterations': 5,
        }
        result = should_continue_verification(state)
        assert result == "code_regeneration"

    def test_should_continue_verification_max_iterations(self):
        """Test that workflow ends when max iterations reached."""
        state = {
            'verification_result': {
                'needs_repair': True,
                'needs_regeneration': False,
            },
            'iteration_count': 5,
            'max_iterations': 5,
        }
        result = should_continue_verification(state)
        assert result == "end"
