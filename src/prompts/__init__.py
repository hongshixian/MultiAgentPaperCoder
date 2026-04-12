"""Prompt templates for MultiAgentPaperCoder agents."""

from pathlib import Path
from typing import Dict, Any


class PromptTemplate:
    """Container for a prompt template and metadata."""

    def __init__(
        self,
        name: str,
        template: str,
        input_variables: list[str],
        output_format: Dict[str, Any],
    ):
        self.name = name
        self.template = template
        self.input_variables = input_variables
        self.output_format = output_format


class PromptManager:
    """Manager for loading and accessing prompt templates."""

    def __init__(self):
        self.templates: Dict[str, PromptTemplate] = {}
        self._load_templates()

    def _load_templates_from_yaml(self, prompts_dir: Path):
        """Load prompt templates from YAML files."""
        try:
            import yaml
        except ImportError:
            return

        for yaml_file in prompts_dir.glob("*.yaml"):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                template_name = data.get("name", yaml_file.stem)
                input_variables = data.get("input_variables", [])
                output_format = data.get("output_format", {})
                template = data.get("template", "")

                self.templates[template_name] = PromptTemplate(
                    name=template_name,
                    template=template,
                    input_variables=input_variables,
                    output_format=output_format,
                )
            except Exception as e:
                print(f"Warning: Failed to load {yaml_file}: {e}")

    def _load_templates_from_txt(self, prompts_dir: Path):
        """Load prompt templates from .txt files (legacy format)."""
        import re

        file_mapping = {
            "analyzer.txt": "algorithm_analyzer",
            "planner.txt": "code_planner",
            "generator.txt": "code_generator",
        }

        for filename, template_name in file_mapping.items():
            file_path = prompts_dir / filename
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    template = f.read()
                variables = list(set(re.findall(r"\{(\w+)\}", template)))
                self.templates[template_name] = PromptTemplate(
                    name=template_name,
                    template=template,
                    input_variables=variables,
                    output_format={},
                )

    def _load_templates(self):
        """Load all prompt templates from known locations."""
        # Locations to search, in priority order
        possible_dirs = [
            Path(__file__).parent,                # src/prompts/  (YAML files live here)
            Path(__file__).parent.parent / "prompts",  # prompts/ at project root
        ]

        for prompts_dir in possible_dirs:
            if not prompts_dir.exists():
                continue
            # Prefer YAML, fall back to TXT
            self._load_templates_from_yaml(prompts_dir)
            if not self.templates:
                self._load_templates_from_txt(prompts_dir)
            if self.templates:
                break

        if not self.templates:
            print("Warning: No prompt templates found")

    def get_template(self, name: str) -> PromptTemplate:
        if name not in self.templates:
            raise KeyError(f"Prompt template '{name}' not found")
        return self.templates[name]

    def get_template_names(self) -> list[str]:
        return list(self.templates.keys())

    def format_template(self, name: str, **kwargs) -> str:
        """Format a template with provided variables."""
        template = self.get_template(name)
        missing = set(template.input_variables) - set(kwargs.keys())
        if missing:
            raise ValueError(
                f"Missing required variables for template '{name}': {missing}"
            )
        return template.template.format(**kwargs)


# Global singleton
PROMPTS = PromptManager()
