# MultiAgentPaperCoder 设计文档

## 项目概述

MultiAgentPaperCoder 是一个基于多智能体系统的自动化论文代码复现工具。该系统能够读取算法论文，理解算法实现，规划复现方案，生成可运行代码，并验证代码的正确性。

## 核心目标

1. 自动化论文算法代码复现流程
2. 降低论文复现的门槛
3. 提供代码生成的可追溯性和可解释性

## 技术栈

| 组件 | 技术选择 | 版本要求 |
|------|----------|----------|
| Python | 3.12+ | conda环境: py12pt |
| LLM | Claude API | 最新版本 |
| 智能体编排 | LangGraph | >=0.2.0 |
| PDF解析 | PyPDF2 + pdfplumber | 最新版本 |
| 代码执行 | subprocess + conda | |

**技术决策说明**：选择 LangGraph 而非 DeepAgents，因为 LangGraph 生态更成熟、文档更完善、社区支持更好。

## Agent 架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│              PaperCoderSuperAgent (主控智能体)               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  协调各子Agent执行流程  │  管理整体状态  │  错误处理  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ↓               ↓               ↓
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │  PDFReader   │ │   Algorithm  │ │  CodePlanner │
    │    Agent     │ │  Analyzer    │ │    Agent     │
    │              │ │    Agent     │ │              │
    │  读取PDF内容 │ │ 分析算法逻辑 │ │ 制定复现计划 │
    └──────────────┘ └──────────────┘ └──────────────┘
           │               │               │
           └───────────────┼───────────────┘
                           ↓
                    ┌──────────────┐
                    │  CodeGenerator│
                    │    Agent      │
                    │              │
                    │  生成Python代码 │
                    └──────────────┘
                           │
                           ↓
                    ┌──────────────┐
                    │  CodeValidator│
                    │    Agent      │
                    │              │
                    │  运行并验证代码│
                    └──────────────┘
```

### 1. PaperCoderSuperAgent（主控智能体）

**角色**： orchestrator / coordinator

**职责**：
- 协调各子Agent的执行顺序
- 维护全局状态（论文处理上下文）
- 处理Agent间的消息传递
- 错误恢复和重试逻辑
- 汇总最终结果

**能力（工具）**：
- State Manager: 管理论文处理状态
- Router: 决定下一个执行的Agent
- Error Handler: 处理失败和重试

**输入**：PDF文件路径
**输出**：完整复现报告

### 2. PDFReaderAgent（论文读取器）

**角色**： document reader

**职责**：
- 读取PDF文件并提取文本
- 识别论文结构（标题、摘要、章节）
- 提取公式和图表描述（可选）
- 清洗和格式化文本内容

**能力（工具）**：
- PDF Parser: PyPDF2/pdfplumber
- Text Cleaner Extractor: 正则表达式清洗
- Structure Parser: 识别论文章节结构

**输入**：pdf_path: str
**输出**：
```python
{
    "full_text": str,           # 完整文本
    "title": str,               # 论文标题
    "abstract": str,            # 摘要
    "sections": List[Dict],      # 章节列表
    "formulas": List[str],      # 提取的公式
    "figures": List[str]        # 图表描述
}
```

### 3. AlgorithmAnalyzerAgent（算法分析器）

**角色**： algorithm extractor

**职责**：
- 分析论文内容，识别算法核心逻辑
- 提取算法的关键步骤和伪代码
- 识别数据流和依赖关系
- 提取超参数、数据集要求等配置信息

**能力（工具/技能）**：
- LLM Inference: Claude API
- Algorithm Detector: 算法名称识别
- Dependency Analyzer: 依赖关系提取
- Parameter Extractor: 超参数提取

**输入**：论文文本内容
**输出**：
```python
{
    "algorithm_name": str,           # 算法名称
    "algorithm_type": str,           # 算法类型（分类/回归/生成等）
    "core_logic": str,               # 核心逻辑描述
    "pseudocode": str,               # 提取的伪代码
    "hyperparameters": Dict,          # 超参数配置
    "requirements": {
        "dataset": str,              # 数据集要求
        "frameworks": List[str],     # 依赖框架
        "compute": str               # 计算资源需求
    },
    "data_flow": str                 # 数据流描述
}
```

### 4. CodePlannerAgent（代码规划器）

**角色**： code architect

**职责**：
- 根据算法分析结果，设计代码结构
- 规划文件组织方案
- 分解实现步骤
- 识别需要的外部依赖

**能力（工具/技能）**：
- LLM Inference: Claude API
- Project Architect: 项目结构设计
- Step Decomposer: 任务分解
- Dependency Resolver: 依赖解析

**输入**：算法分析报告
**输出**：
```python
{
    "project_structure": List[Dict],  # 文件结构
    "implementation_steps": List[str], # 实现步骤
    "dependencies": {
        "python_packages": List[str], # Python依赖
        "system_packages": List[str]  # 系统依赖
    },
    "entry_points": List[str],        # 入口文件
    "test_plan": str                  # 测试计划
}
```

### 5. CodeGeneratorAgent（代码生成器）

**角色**： code writer

**职责**：
- 根据规划生成完整的Python代码
- 生成数据加载模块
- 生成模型定义模块
- 生成训练/推理脚本
- 生成配置文件

**能力（工具/技能）**：
- LLM Inference: Claude API
- Code Templater: 代码模板引擎
- File Writer: 文件写入操作
- Module Organizer: 模块组织

**输入**：代码规划文档
**输出**：
```python
{
    "generated_files": List[Dict],  # 生成的文件列表
    "file_paths": List[str],        # 文件路径
    "code_stats": Dict              # 代码统计信息
}
```

### 6. CodeValidatorAgent（代码验证器）

**角色**： code tester

**职责**：
- 在指定conda环境中运行代码
- 监控执行过程和输出
- �分析错误日志
- 提供修复建议

**能力（工具/技能）**：
- Conda Manager: conda环境管理
- subprocess Executor: 代码执行
- Log Analyzer: 日志分析
- Debugger: 错误诊断和修复建议

**输入**：生成的代码路径
**输出**：
```python
{
    "status": str,                   # success/failed/partial
    "execution_time": float,         # 执行时间
    "error_log": str,                # 错误日志
    "fix_suggestions": List[str],     # 修复建议
    "validation_report": str         # 验证报告
}
```

## 工作流设计

### 状态定义

```python
from typing import TypedDict, List, Dict, Optional

class PaperState(TypedDict):
    # 输入
    pdf_path: str

    # PDF读取结果
    paper_content: Optional[Dict]

    # 算法分析结果
    algorithm_analysis: Optional[Dict]

    # 代码规划结果
    code_plan: Optional[Dict]

    # 代码生成结果
    generated_code: Optional[Dict]

    # 验证结果
    validation_result: Optional[Dict]

    # 控制信息
    current_step: str
    errors: List[str]
    retry_count: int
    max_retries: int
```

### 工作流图

```
Start
  │
  ├─→ PDFReaderAgent
  │     ↓ (success)
  │     AlgorithmAnalyzerAgent
  │           ↓ (success)
  │           CodePlannerAgent
  │                 ↓ (success)
  │                 CodeGeneratorAgent
  │                       ↓ (success)
  │                       CodeValidatorAgent
  │                             ↓
  │                             End (success)
  │
  └─→ Handle Errors ←── (failed)
        ↓
    Retry or Exit
```

### 决策逻辑

1. 顺序执行：各Agent按顺序执行，前一个成功后执行下一个
2. 错误处理：遇到错误时，根据错误类型决定重试或退出
3. 验证失败反馈：如果代码验证失败，可以回退到代码生成阶段

## 依赖管理

### Python依赖

```
langgraph>=0.2.0
langchain>=0.2.0
anthropic>=0.25.0
PyPDF2>=3.0.0
pdfplumber>=0.10.0
pydantic>=2.0.0
python-dotenv>=1.0.0
```

### 系统依赖

- conda/miniconda
- Python 3.12+
- CUDA（如果涉及GPU训练）

## 安全考虑

1. **代码沙箱执行**：生成的代码在隔离的conda环境中执行
2. **输入验证**：严格验证PDF文件路径
3. **权限控制**：限制代码执行的文件系统访问权限
4. **资源限制**：设置内存和CPU使用上限

## 可扩展性

1. **插件化Agent**：支持动态添加新的Agent
2. **自定义Prompt**：支持用户自定义提示词模板
3. **多LLM支持**：支持切换不同的LLM后端
4. **分布式执行**：未来支持多节点并行执行

## 性能优化

1. **LLM调用缓存**：缓存相同的LLM查询结果
2. **并行处理**：独立的任务可以并行执行
3. **流式输出**：支持实时输出生成进度
4. **增量更新**：支持只重新执行失败的步骤

## 文档说明

本文档将随着项目开发进展持续更新，保持与实际代码实现的一致性。
