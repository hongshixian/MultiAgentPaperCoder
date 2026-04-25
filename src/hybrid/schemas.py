"""Pydantic schemas for structured sub-agent output.

Each sub-agent returns one of these models via create_agent(response_format=...).
The router reads specific boolean/enum fields directly from state updates
derived from these models, ensuring deterministic routing.
"""

from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field


class DocumentAnalysisResult(BaseModel):
    """Structured output from the document-analyst sub-agent."""

    title: str = Field(description="论文名称")
    problem: str = Field(description="论文解决的问题")
    method_summary: str = Field(description="方法概要")
    modules_to_implement: List[str] = Field(description="需要实现的模块列表")
    training_flow: List[str] = Field(description="训练流程步骤")
    evaluation_flow: List[str] = Field(description="评估流程步骤")
    dependencies: List[str] = Field(description="Python 依赖包")
    risks: List[str] = Field(description="复现风险")
    artifact_path: str = Field(description="写入的分析文件路径")


class CodeGenerationResult(BaseModel):
    """Structured output from the code-generator sub-agent."""

    files_written: List[str] = Field(description="生成的文件路径列表")
    entry_point: str = Field(description="入口文件，默认 main.py")
    summary: str = Field(description="生成代码的简要说明")
    code_dir: str = Field(description="代码目录路径")


class VerificationResult(BaseModel):
    """Structured output from the code-verifier sub-agent."""

    passed: bool = Field(
        description="代码执行是否通过（exit_code == 0 且无错误）"
    )
    error_type: Literal[
        "import_error", "syntax_error", "runtime_error", "logic_error", "none"
    ] = Field(description="错误类型分类")
    error_cause: str = Field(
        description="具体的错误原因，引用 stderr 原文关键行"
    )
    error_location: str = Field(
        description="出错文件和行号，如 main.py:42。无法定位则填 unknown"
    )
    stdout_summary: str = Field(description="程序标准输出的简要总结")
    needs_repair: bool = Field(description="代码是否需要修复才能通过")


class RepairResult(BaseModel):
    """Structured output from the error-repairer sub-agent."""

    files_modified: List[str] = Field(description="修改的文件列表")
    repair_summary: str = Field(description="修复方案说明")
    root_cause: str = Field(description="根因分析")
