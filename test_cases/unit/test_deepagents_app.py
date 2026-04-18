"""Tests for the DeepAgents-based app package."""

from __future__ import annotations

import sys

import pytest

from app.agent import build_agent
from app.config import Settings
from app.main import build_user_prompt
from app.tools.artifact_tools import list_files, read_text_file, save_text_file
from app.tools.exec_tools import check_entrypoint_exists, python_syntax_check


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
        assert captured["debug"] is True


class TestMainPrompt:
    """Tests for the CLI user prompt builder."""

    def test_build_user_prompt_contains_paths(self):
        prompt = build_user_prompt("/tmp/paper.pdf", "./output")
        assert "/tmp/paper.pdf" in prompt
        assert "./output/generated_code/" in prompt
        assert "read_pdf_text" in prompt
