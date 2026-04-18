"""Agents for MultiAgentPaperCoder.

This module exports the 4 core agents as defined in the architecture:
- DocumentAnalysisAgent: Reads and analyzes research papers
- CodeGenerationAgent: Plans and generates implementation code
- CodeVerificationAgent: Validates and verifies generated code
- ErrorRepairAgent: Analyzes and repairs code errors
"""

from .base import BaseAgent
from .document_analysis_agent import DocumentAnalysisAgent
from .code_generation_agent import CodeGenerationAgent
from .code_verification_agent import CodeVerificationAgent
from .error_repair_agent import ErrorRepairAgent

__all__ = [
    "BaseAgent",
    "DocumentAnalysisAgent",
    "CodeGenerationAgent",
    "CodeVerificationAgent",
    "ErrorRepairAgent",
]
