"""Tests for the hybrid workflow implementation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.hybrid.config import Settings
from src.hybrid.schemas import (
    CodeGenerationResult,
    DocumentAnalysisResult,
    RepairResult,
    VerificationResult,
)
from src.hybrid.state import PaperState
from src.hybrid.tools.artifact_tools import list_files, read_text_file, save_text_file
from src.hybrid.tools.exec_tools import (
    check_entrypoint_exists,
    install_requirements,
    python_syntax_check,
    run_python_entrypoint,
)
from src.hybrid.workflow import create_workflow, should_continue_verification


# ---------------------------------------------------------------------------
# Router logic tests
# ---------------------------------------------------------------------------


class TestRouter:
    """Deterministic routing logic — no LLM involved."""

    def test_needs_repair_below_max(self):
        state: PaperState = {
            "needs_repair": True,
            "iteration_count": 0,
            "max_iterations": 5,
        }
        assert should_continue_verification(state) == "error_repair"

    def test_needs_repair_at_max(self):
        state: PaperState = {
            "needs_repair": True,
            "iteration_count": 5,
            "max_iterations": 5,
        }
        assert should_continue_verification(state) == "end"

    def test_needs_repair_above_max(self):
        state: PaperState = {
            "needs_repair": True,
            "iteration_count": 6,
            "max_iterations": 5,
        }
        assert should_continue_verification(state) == "end"

    def test_passed_no_repair(self):
        state: PaperState = {
            "needs_repair": False,
            "iteration_count": 0,
            "max_iterations": 5,
        }
        assert should_continue_verification(state) == "end"

    def test_analysis_failed_terminates(self):
        state: PaperState = {
            "analysis_status": "failed",
            "needs_repair": True,
            "iteration_count": 0,
            "max_iterations": 5,
        }
        assert should_continue_verification(state) == "end"

    def test_generation_failed_terminates(self):
        state: PaperState = {
            "generation_status": "failed",
            "needs_repair": True,
            "iteration_count": 0,
            "max_iterations": 5,
        }
        assert should_continue_verification(state) == "end"

    def test_default_values_no_repair(self):
        """Empty state defaults to no repair needed."""
        state: PaperState = {}
        assert should_continue_verification(state) == "end"

    def test_repair_midway(self):
        state: PaperState = {
            "needs_repair": True,
            "iteration_count": 3,
            "max_iterations": 5,
        }
        assert should_continue_verification(state) == "error_repair"


# ---------------------------------------------------------------------------
# State tests
# ---------------------------------------------------------------------------


class TestPaperState:
    """State field assignments and defaults."""

    def test_initial_state(self):
        state: PaperState = {
            "pdf_path": "/tmp/paper.pdf",
            "iteration_count": 0,
            "max_iterations": 5,
            "errors": [],
        }
        assert state["pdf_path"] == "/tmp/paper.pdf"
        assert state["iteration_count"] == 0

    def test_analysis_completed(self):
        state: PaperState = {
            "analysis_path": "/output/paper_analysis.md",
            "analysis_status": "completed",
        }
        assert state["analysis_status"] == "completed"

    def test_verification_failed(self):
        state: PaperState = {
            "verification_passed": False,
            "error_type": "import_error",
            "error_cause": "ModuleNotFoundError: numpy",
            "error_location": "main.py:3",
            "needs_repair": True,
        }
        assert state["verification_passed"] is False
        assert state["error_type"] == "import_error"


# ---------------------------------------------------------------------------
# Pydantic schema tests
# ---------------------------------------------------------------------------


class TestSchemas:
    """Schema validation for structured sub-agent output."""

    def test_document_analysis_result(self):
        result = DocumentAnalysisResult(
            title="Test Paper",
            problem="Test problem",
            method_summary="Test method",
            modules_to_implement=["module_a"],
            training_flow=["step1"],
            evaluation_flow=["step1"],
            dependencies=["numpy"],
            risks=["risk1"],
            artifact_path="/output/paper_analysis.md",
        )
        assert result.title == "Test Paper"
        assert result.artifact_path == "/output/paper_analysis.md"

    def test_code_generation_result(self):
        result = CodeGenerationResult(
            files_written=["/output/main.py"],
            entry_point="main.py",
            summary="Test generation",
            code_dir="/output/generated_code",
        )
        assert len(result.files_written) == 1

    def test_verification_result_passed(self):
        result = VerificationResult(
            passed=True,
            error_type="none",
            error_cause="",
            error_location="unknown",
            stdout_summary="ok",
            needs_repair=False,
        )
        assert result.passed is True
        assert result.needs_repair is False

    def test_verification_result_failed(self):
        result = VerificationResult(
            passed=False,
            error_type="runtime_error",
            error_cause="ZeroDivisionError: division by zero",
            error_location="main.py:10",
            stdout_summary="",
            needs_repair=True,
        )
        assert result.error_type == "runtime_error"
        assert result.needs_repair is True

    def test_repair_result(self):
        result = RepairResult(
            files_modified=["main.py"],
            repair_summary="Fixed division by zero",
            root_cause="Missing zero check",
        )
        assert "main.py" in result.files_modified

    def test_verification_result_invalid_error_type(self):
        with pytest.raises(Exception):
            VerificationResult(
                passed=False,
                error_type="invalid_type",
                error_cause="test",
                error_location="unknown",
                stdout_summary="",
                needs_repair=True,
            )


# ---------------------------------------------------------------------------
# Artifact tools tests
# ---------------------------------------------------------------------------


class TestArtifactTools:
    """File artifact tools with path sandbox."""

    def test_save_and_read_text_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OUTPUT_ROOT", str(tmp_path / "output"))
        file_path = tmp_path / "output" / "artifacts" / "note.txt"

        result = save_text_file(str(file_path), "hello")
        assert result.startswith("saved:")
        assert read_text_file(str(file_path)) == "hello"

    def test_save_text_file_blocks_writes_outside_output_root(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OUTPUT_ROOT", str(tmp_path / "output"))
        with pytest.raises(ValueError, match="Path must stay under"):
            save_text_file(str(tmp_path / "outside.txt"), "nope")

    def test_list_files_returns_saved_files(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("OUTPUT_ROOT", str(tmp_path / "output"))
        save_text_file(str(tmp_path / "output" / "artifacts" / "a.txt"), "a")
        save_text_file(str(tmp_path / "output" / "generated_code" / "main.py"), "print('x')")

        listed = list_files("output")
        assert "a.txt" in listed
        assert "main.py" in listed


# ---------------------------------------------------------------------------
# Exec tools tests
# ---------------------------------------------------------------------------


class TestExecTools:
    """Deterministic execution tools."""

    def test_python_syntax_check_passes(self, tmp_path):
        file_path = tmp_path / "main.py"
        file_path.write_text("print('ok')\n", encoding="utf-8")
        result = python_syntax_check(str(tmp_path))
        assert result.startswith("PASSED")

    def test_python_syntax_check_reports_errors(self, tmp_path):
        file_path = tmp_path / "broken.py"
        file_path.write_text("def broken(:\n", encoding="utf-8")
        result = python_syntax_check(str(tmp_path))
        assert result.startswith("FAILED")

    def test_check_entrypoint_exists(self, tmp_path):
        (tmp_path / "main.py").write_text("print('ok')\n", encoding="utf-8")
        assert check_entrypoint_exists(str(tmp_path)).startswith("FOUND")
        assert check_entrypoint_exists(str(tmp_path / "missing")).startswith("MISSING")

    def test_run_python_entrypoint_captures_output(self, tmp_path):
        (tmp_path / "main.py").write_text("print('hello from main')\n", encoding="utf-8")
        result = run_python_entrypoint(str(tmp_path))
        assert result.startswith("PASSED")
        assert "hello from main" in result

    def test_run_python_entrypoint_reports_missing_entrypoint(self, tmp_path):
        result = run_python_entrypoint(str(tmp_path))
        assert result.startswith("NOT_RUN")

    def test_install_requirements_not_found(self, tmp_path):
        result = install_requirements(str(tmp_path))
        assert result.startswith("NOT_FOUND")

    def test_install_requirements_with_file(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("# empty\n", encoding="utf-8")
        result = install_requirements(str(tmp_path))
        # Should either PASSED or FAILED (depends on env), not NOT_FOUND
        assert not result.startswith("NOT_FOUND")


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------


class TestSettings:
    """Runtime settings."""

    def test_ensure_dirs_creates_output_structure(self, tmp_path):
        settings = Settings(output_root=tmp_path / "output")
        settings.ensure_dirs()
        assert settings.output_root.exists()
        assert settings.artifacts_dir.exists()
        assert settings.generated_code_dir.exists()
        assert settings.log_dir.exists()

    def test_resolved_model_name_strips_provider_prefix(self, tmp_path):
        settings = Settings(model_name="openai:gpt-4o", output_root=tmp_path / "output")
        assert settings.resolved_model_name == "gpt-4o"

    def test_create_run_output_root_uses_pdf_stem(self, tmp_path):
        settings = Settings(output_root=tmp_path / "output")
        run_dir = settings.create_run_output_root(tmp_path / "paper.pdf")
        assert run_dir.parent == tmp_path / "output"
        assert run_dir.name.endswith("_paper")

    def test_settings_expose_required_artifact_paths(self, tmp_path):
        settings = Settings(output_root=tmp_path / "output")
        assert settings.paper_analysis_path == tmp_path / "output" / "artifacts" / "paper_analysis.md"


# ---------------------------------------------------------------------------
# Workflow build test
# ---------------------------------------------------------------------------


class TestWorkflowBuild:
    """Verify the workflow graph compiles."""

    def test_create_workflow_returns_compiled_graph(self, tmp_path):
        from langgraph.graph.state import CompiledStateGraph

        settings = Settings(output_root=tmp_path / "output")
        workflow = create_workflow(settings)
        assert isinstance(workflow, CompiledStateGraph)
