"""Pytest shared fixtures for MultiAgentPaperCoder tests."""

import os
import sys
import tempfile
from pathlib import Path
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture
def test_config():
    """Provide test configuration."""
    return {
        "output_dir": tempfile.mkdtemp(),
        "conda_env_name": "py12pt",
        "verbose": True,
        "skip_validation": True,  # Skip validation in tests to save time
    }


@pytest.fixture
def sample_pdf_path():
    """Provide path to a sample PDF file."""
    pdf_dir = Path(__file__).parent / "paper_examples"
    if pdf_dir.exists():
        pdfs = list(pdf_dir.glob("*.pdf"))
        if pdfs:
            return str(pdfs[0])  # Return first PDF
    return None


@pytest.fixture
def temp_output_dir():
    """Create and clean up temporary output directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)
