"""State management for MultiAgentPaperCoder."""

from typing import TypedDict, List, Dict, Optional, Any


class PaperState(TypedDict, total=False):
    """State for paper processing workflow.

    This class defines the structure of the state that flows through
    the agent graph during paper processing.
    """

    # Input
    pdf_path: str

    # PDF reading result
    paper_content: Optional[Dict[str, Any]]

    # Algorithm analysis result
    algorithm_analysis: Optional[Dict[str, Any]]

    # Code planning result
    code_plan: Optional[Dict[str, Any]]

    # Code generation result
    generated_code: Optional[Dict[str, Any]]

    # Validation result
    validation_result: Optional[Dict[str, Any]]

    # Control information
    current_step: str
    errors: List[str]
    retry_count: int
    max_retries: int
