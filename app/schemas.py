"""Structured schemas used by DeepAgents subagents."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PaperAnalysis(BaseModel):
    """Structured paper analysis for downstream generation."""

    title: str = Field(description="Paper title")
    problem: str = Field(description="Problem statement solved by the paper")
    method_summary: str = Field(description="High-level method summary")
    modules_to_implement: list[str] = Field(description="Core modules that need implementation")
    training_flow: list[str] = Field(description="Training flow steps")
    evaluation_flow: list[str] = Field(description="Evaluation flow steps")
    dependencies: list[str] = Field(description="Likely Python dependencies")
    risks: list[str] = Field(description="Main reproduction risks")


class VerificationReport(BaseModel):
    """Structured verification result."""

    success: bool = Field(description="Whether verification passed")
    checked_files: list[str] = Field(description="Files checked during verification")
    errors: list[str] = Field(description="Collected errors")
    summary: str = Field(description="Verification summary")


class RepairPlan(BaseModel):
    """Structured repair plan for a failed generation."""

    root_cause: str = Field(description="Root cause analysis")
    files_to_modify: list[str] = Field(description="Files that should be modified")
    repair_strategy: str = Field(description="Repair strategy summary")
