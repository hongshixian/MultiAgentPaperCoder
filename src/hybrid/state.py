"""State definition for the hybrid workflow.

State carries only lightweight metadata (paths, status, error info),
not artifact content. Agents exchange content through the filesystem.
"""

from typing import List, Literal, Optional

from typing import TypedDict


class PaperState(TypedDict, total=False):
    """State for the paper reproduction workflow.

    Fields are grouped by workflow stage. All artifact *content* lives on
    disk; state only records paths and structured results.
    """

    # ---- Input ----
    pdf_path: str

    # ---- Document analysis ----
    analysis_path: str  # paper_analysis.md path
    analysis_status: Literal["completed", "failed"]

    # ---- Code generation ----
    code_dir: str  # generated_code/ directory path
    file_list: List[str]  # generated file names
    generation_status: Literal["completed", "failed"]

    # ---- Code verification ----
    verification_passed: bool  # exit_code == 0 and no errors
    error_type: Literal[
        "import_error", "syntax_error", "runtime_error", "logic_error", "none"
    ]
    error_cause: str  # specific error reason, quoting stderr
    error_location: str  # file and line, e.g. main.py:42
    stdout_summary: str  # brief summary of program output
    needs_repair: bool  # whether code needs fixing

    # ---- Error repair ----
    repair_status: Literal["completed", "failed"]
    files_modified: List[str]  # files changed in this repair

    # ---- Loop control ----
    iteration_count: int  # current repair iteration
    max_iterations: int  # max repair iterations, default 5

    # ---- Error log ----
    errors: List[str]  # accumulated error messages
