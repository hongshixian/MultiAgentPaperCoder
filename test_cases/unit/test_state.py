"""Unit tests for state module."""

from src.state import PaperState


class TestPaperState:
    """Test cases for PaperState TypedDict."""

    def test_paper_state_fields(self):
        """Test that PaperState has all expected fields."""
        # Create a minimal valid state
        state: PaperState = {
            'pdf_path': '/test/paper.pdf',
        }

        assert state['pdf_path'] == '/test/paper.pdf'
        assert state.get('paper_content') is None
        assert state.get('algorithm_analysis') is None

    def test_paper_state_with_all_fields(self):
        """Test PaperState with all optional fields populated."""
        state: PaperState = {
            'pdf_path': '/test/paper.pdf',
            'paper_content': {'title': 'Test Paper'},
            'algorithm_analysis': {'algorithm_name': 'Test Algo'},
            'code_plan': {'project_structure': []},
            'generated_code': {'files': []},
            'validation_result': {'status': 'success'},
            'verification_result': {'quality_score': 90},
            'repair_history': [],
            'current_step': 'completed',
            'errors': [],
            'retry_count': 0,
            'max_retries': 3,
            'iteration_count': 0,
            'max_iterations': 5,
        }

        assert state['pdf_path'] == '/test/paper.pdf'
        assert state['paper_content']['title'] == 'Test Paper'
        assert state['algorithm_analysis']['algorithm_name'] == 'Test Algo'
        assert state['verification_result']['quality_score'] == 90
