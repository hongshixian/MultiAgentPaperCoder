"""Tests for the DeepAgents-based app package."""

from __future__ import annotations

import sys

import pytest

from app.agent import build_agent
from app.bootstrap import (
    apply_known_runtime_repairs,
    ensure_minimum_generated_project,
    generate_verification_report,
)
from app.config import Settings
from app.main import build_user_prompt
from app.tools.artifact_tools import list_files, read_text_file, save_text_file
from app.tools.exec_tools import check_entrypoint_exists, python_syntax_check, run_python_entrypoint


class TestSettings:
    """Tests for runtime settings."""

    def test_ensure_dirs_creates_output_structure(self, tmp_path):
        settings = Settings(output_root=tmp_path / "output")
        settings.ensure_dirs()

        assert settings.output_root.exists()
        assert settings.artifacts_dir.exists()
        assert settings.generated_code_dir.exists()
        assert settings.log_dir.exists()

    def test_resolved_model_name_strips_provider_prefix(self, tmp_path):
        settings = Settings(model_name="openai:gpt-5.4", output_root=tmp_path / "output")
        assert settings.resolved_model_name == "gpt-5.4"

    def test_create_run_output_root_uses_pdf_stem(self, tmp_path):
        settings = Settings(output_root=tmp_path / "output")
        run_dir = settings.create_run_output_root(tmp_path / "paper.pdf")
        assert run_dir.parent == tmp_path / "output"
        assert run_dir.name.endswith("_paper")

    def test_settings_expose_required_artifact_paths(self, tmp_path):
        settings = Settings(output_root=tmp_path / "output")
        assert settings.paper_analysis_path == tmp_path / "output" / "artifacts" / "paper_analysis.txt"
        assert settings.verification_report_path == tmp_path / "output" / "artifacts" / "verification_report.txt"


class TestArtifactTools:
    """Tests for file artifact tools."""

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


class TestExecTools:
    """Tests for deterministic verification tools."""

    def test_python_syntax_check_passes(self, tmp_path):
        file_path = tmp_path / "main.py"
        file_path.write_text("print('ok')\n", encoding="utf-8")

        result = python_syntax_check(str(tmp_path))

        assert result.startswith("PASSED")
        assert str(file_path) in result

    def test_python_syntax_check_reports_errors(self, tmp_path):
        file_path = tmp_path / "broken.py"
        file_path.write_text("def broken(:\n", encoding="utf-8")

        result = python_syntax_check(str(tmp_path))

        assert result.startswith("FAILED")
        assert "broken.py" in result

    def test_check_entrypoint_exists(self, tmp_path):
        file_path = tmp_path / "main.py"
        file_path.write_text("print('ok')\n", encoding="utf-8")

        assert check_entrypoint_exists(str(tmp_path)).startswith("FOUND")
        assert check_entrypoint_exists(str(tmp_path / "missing")).startswith("MISSING")

    def test_run_python_entrypoint_captures_output(self, tmp_path):
        file_path = tmp_path / "main.py"
        file_path.write_text("print('hello from main')\n", encoding="utf-8")

        result = run_python_entrypoint(str(tmp_path))

        assert result.startswith("PASSED")
        assert "hello from main" in result

    def test_run_python_entrypoint_reports_missing_entrypoint(self, tmp_path):
        result = run_python_entrypoint(str(tmp_path))
        assert result.startswith("NOT_RUN")


class TestAppAgent:
    """Tests for the DeepAgents app builder."""

    def test_build_agent_raises_without_dependency(self, tmp_path, monkeypatch):
        monkeypatch.setitem(sys.modules, "deepagents", None)
        with pytest.raises(ImportError, match="deepagents is not installed"):
            build_agent(Settings(output_root=tmp_path / "output"))

    def test_build_agent_constructs_main_agent(self, tmp_path, monkeypatch):
        captured = {}

        def fake_create_agent(**kwargs):
            captured.update(kwargs)
            return {"ok": True, "kwargs": kwargs}

        monkeypatch.setattr("app.agent.create_agent", fake_create_agent)
        monkeypatch.setattr(
            "app.agent.build_subagents",
            lambda settings: [
                {
                    "name": "document-analyst",
                    "description": "doc agent",
                    "runnable": object(),
                }
            ],
        )

        result = build_agent(Settings(output_root=tmp_path / "output"))

        assert result["ok"] is True
        assert captured["name"] == "papercoder-main"
        assert captured["middleware"]
        assert captured["checkpointer"] is not None
        assert captured["debug"] is False


class TestMainPrompt:
    """Tests for the CLI user prompt builder."""

    def test_build_user_prompt_contains_paths(self):
        prompt = build_user_prompt("/tmp/paper.pdf", "./output")
        assert "./output/generated_code/" in prompt
        assert "./output/artifacts/paper_analysis.txt" in prompt
        assert "Write main.py and requirements.txt before writing any optional extra modules." in prompt
        assert "source of truth for code generation" in prompt
        assert "brand-new empty workspace" in prompt


class TestVerificationReport:
    """Tests for deterministic verification report generation."""

    def test_ensure_minimum_generated_project_creates_fallback_main(self, tmp_path):
        settings = Settings(output_root=tmp_path / "output")
        settings.ensure_dirs()
        (settings.generated_code_dir / "helper.py").write_text("VALUE = 1\n", encoding="utf-8")

        main_path = ensure_minimum_generated_project(settings)

        assert main_path.exists()
        assert "Fallback entrypoint" in main_path.read_text(encoding="utf-8")

    def test_generate_verification_report_includes_runtime_section(self, tmp_path, monkeypatch):
        settings = Settings(output_root=tmp_path / "output")
        settings.ensure_dirs()
        monkeypatch.setenv("OUTPUT_ROOT", str(settings.output_root))
        (settings.generated_code_dir / "main.py").write_text("print('ok')\n", encoding="utf-8")
        (settings.generated_code_dir / "requirements.txt").write_text("numpy\n", encoding="utf-8")

        report_path = generate_verification_report(settings)
        report_text = report_path.read_text(encoding="utf-8")

        assert "Layer 1: Deterministic Static Verification" in report_text
        assert "Layer 2: Runtime Execution Verification" in report_text
        assert "STDOUT:" in report_text

    def test_apply_known_runtime_repairs_adds_huffman_comparator(self, tmp_path):
        settings = Settings(output_root=tmp_path / "output")
        settings.ensure_dirs()
        main_text = """
class HuffmanNode:
    def __init__(self, idx=None, count=0):
        self.idx = idx
        self.count = count
"""
        (settings.generated_code_dir / "main.py").write_text(main_text, encoding="utf-8")

        actions = apply_known_runtime_repairs(
            settings,
            "TypeError: '<' not supported between instances of 'HuffmanNode' and 'HuffmanNode'",
        )

        updated = (settings.generated_code_dir / "main.py").read_text(encoding="utf-8")
        assert actions
        assert "def __lt__(" in updated
