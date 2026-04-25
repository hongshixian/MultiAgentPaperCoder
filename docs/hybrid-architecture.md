# 混合架构实现指南

## 概述

MultiAgentPaperCoder 采用**混合架构**，结合了 LangGraph 和 LangChain Agents 两种框架的优势：

- **LangGraph**: 用于确定性的工作流编排、状态管理和条件路由
- **LangChain Agents**: 用于子智能体专业化、工具调用和结构化输出

这种架构在保留工作流控制力的同时，获得了子智能体的灵活性。

## 架构对比

### 纯 LangGraph 架构

```
┌─────────────────────────────────────┐
│      LangGraph StateGraph          │
│  ┌──────────┐ ┌──────────┐      │
│  │  Node 1  │ │  Node 2  │ ...  │
│  └──────────┘ └──────────┘      │
│         ↓           ↓              │
│  ┌──────────────────────────┐      │
│  │   Conditional Router    │      │
│  └──────────────────────────┘      │
└─────────────────────────────────────┘
```

**优点**：
- 完全确定性的状态管理
- 清晰的工作流可视化
- 强大的循环和分支控制

**缺点**：
- 子节点实现较为复杂
- 工具调用需要手动管理
- 结构化输出需要额外处理

### 纯 DeepAgents/LangChain 架构

```
┌─────────────────────────────────────┐
│       Main Agent (LLM)            │
│  ┌──────────────────────────┐      │
│  │   Sub-Agent Dispatcher   │      │
│  └──────────────────────────┘      │
│         ↓         ↓               │
│  ┌──────────┐ ┌──────────┐      │
│  │ Sub-Agent │ │ Sub-Agent │ ...  │
│  └──────────┘ └──────────┘      │
└─────────────────────────────────────┘
```

**优点**：
- 快速开发和迭代
- 子智能体易于管理
- 工具调用自动处理
- 结构化输出内置支持

**缺点**：
- 流程控制不够严格
- 难以保证固定顺序
- 调试困难

### 混合架构

```
┌─────────────────────────────────────┐
│      LangGraph StateGraph          │
│  ┌──────────────────────────┐      │
│  │  LangChain Agent Nodes   │      │
│  │  ┌──────────┐          │      │
│  │  │ Sub-Agent │          │      │
│  │  └──────────┘          │      │
│  └──────────────────────────┘      │
│         ↓                          │
│  ┌──────────────────────────┐      │
│  │   Conditional Router    │      │
│  │   (Pure Logic)         │      │
│  └──────────────────────────┘      │
└─────────────────────────────────────┘
```

**优点**：
- LangGraph 提供确定性的工作流控制
- LangChain Agents 提供灵活的子智能体能力
- 状态管理和路由逻辑清晰分离
- 易于调试和可视化

**缺点**：
- 稍微复杂一些的学习曲线

## 实现细节

### 目录结构

```
src/hybrid/
├── __init__.py
├── main.py              # CLI 入口
├── config.py            # Settings + LLM 构建
├── agents.py            # 4 个子智能体节点函数
├── workflow.py          # LangGraph StateGraph
├── state.py             # PaperState TypedDict
├── schemas.py           # Pydantic 结构化输出
├── prompts.py           # 子智能体系统提示词
├── logging_utils.py     # 日志配置
├── callbacks.py         # LangChain 回调处理器
└── tools/              # 工具层
    ├── __init__.py
    ├── pdf_tools.py
    ├── artifact_tools.py
    └── exec_tools.py
```

### 核心组件

#### 1. 状态管理（state.py）

```python
from typing import TypedDict

class PaperState(TypedDict, total=False):
    # 输入
    pdf_path: str
    
    # 文档分析结果
    analysis_path: str
    analysis_status: str
    
    # 代码生成结果
    code_dir: str
    file_list: list[str]
    generation_status: str
    
    # 验证结果
    verification_passed: bool
    error_type: str
    error_cause: str
    error_location: str
    stdout_summary: str
    needs_repair: bool
    
    # 错误修复结果
    repair_status: str
    files_modified: list[str]
    
    # 控制字段
    iteration_count: int
    max_iterations: int
    errors: list[str]
```

#### 2. 子智能体节点（agents.py）

每个节点函数创建一个 LangChain agent：

```python
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from .callbacks import PapercoderCallbackHandler

def document_analysis_node(state: PaperState, config: dict) -> dict:
    settings: Settings = config["settings"]
    
    agent = create_agent(
        model=settings.build_llm(),
        tools=[read_pdf_text, save_text_file],
        system_prompt=DOCUMENT_ANALYSIS_PROMPT,
        response_format=DocumentAnalysisResult,  # 结构化输出
        name="document-analyst",
    )
    
    result = agent.invoke(
        {"messages": [HumanMessage(content=prompt)]},
        config={"callbacks": [PapercoderCallbackHandler()]},
    )
    
    structured = result.get("structured_response")
    return {"analysis_path": structured.artifact_path, ...}
```

#### 3. 工作流编排（workflow.py）

使用 LangGraph StateGraph 编排节点：

```python
from langgraph.graph import StateGraph, END

def create_workflow(settings: Settings) -> StateGraph:
    workflow = StateGraph(PaperState)
    
    # 添加节点
    workflow.add_node("document_analysis", document_analysis_node)
    workflow.add_node("code_generation", code_generation_node)
    workflow.add_node("code_verification", code_verification_node)
    workflow.add_node("error_repair", error_repair_node)
    
    # 设置入口和边
    workflow.set_entry_point("document_analysis")
    workflow.add_edge("document_analysis", "code_generation")
    workflow.add_edge("code_generation", "code_verification")
    workflow.add_conditional_edges(
        "code_verification",
        should_continue_verification,
        {"error_repair": "error_repair", "end": END},
    )
    workflow.add_edge("error_repair", "code_verification")
    
    return workflow.compile()
```

#### 4. 确定性路由（workflow.py）

```python
def should_continue_verification(state: PaperState) -> str:
    """纯逻辑路由，无 LLM 参与"""
    
    # 前置失败则终止
    if state.get("analysis_status") != "completed":
        return "end"
    if state.get("generation_status") != "completed":
        return "end"
    
    # 验证通过则终止
    if not state.get("needs_repair", False):
        return "end"
    
    # 检查迭代次数
    iteration = state.get("iteration_count", 0)
    max_iter = state.get("max_iterations", 5)
    
    if iteration >= max_iter:
        return "end"
    
    return "error_repair"
```

#### 5. 结构化输出（schemas.py）

所有子智能体返回 Pydantic 模型：

```python
from pydantic import BaseModel, Field

class DocumentAnalysisResult(BaseModel):
    title: str = Field(description="论文标题")
    problem: str = Field(description="论文解决的问题")
    method_summary: str = Field(description="方法总体描述")
    modules_to_implement: list[str] = Field(description="需要实现的核心模块")
    training_flow: list[str] = Field(description="训练流程")
    evaluation_flow: list[str] = Field(description="评估流程")
    dependencies: list[str] = Field(description="推测的 Python 依赖")
    risks: list[str] = Field(description="复现风险点")
    artifact_path: str = Field(description="分析报告保存路径")
```

#### 6. 日志系统（callbacks.py + logging_utils.py）

**控制台日志**：
```python
def setup_console_logging(level: str = "info") -> None:
    root = logging.getLogger("papercoder")
    console = logging.StreamHandler(sys.stdout)
    
    if level == "debug":
        console.setLevel(logging.DEBUG)
        root.setLevel(logging.DEBUG)
    else:
        console.setLevel(logging.INFO)
        root.setLevel(logging.INFO)
    
    root.addHandler(console)
```

**结构化回调**：
```python
class PapercoderCallbackHandler(BaseCallbackHandler):
    """LangChain 回调处理器，提供结构化日志"""
    
    def on_chat_model_start(self, serialized, messages, run_id, **kwargs):
        logger.info("Agent正在思考...")
        logger.debug("LLM请求: %s", content[:500])
    
    def on_llm_end(self, response, run_id, **kwargs):
        logger.debug("LLM响应: %s", content[:2000])
    
    def on_tool_start(self, serialized, input_str, run_id, **kwargs):
        tool_name = serialized.get("name", "unknown")
        logger.info("Agent调用了工具: %s", tool_name)
    
    def on_tool_end(self, output, run_id, **kwargs):
        logger.info("工具执行完成: %s", output[:200])
```

## 运行流程

1. **CLI 解析** (`main.py`)
   - 解析参数（`--pdf`, `--output-dir`, `--max-iterations`, `--log-level`）
   - 设置控制台日志
   - 创建文件日志器
   - 创建运行输出目录

2. **工作流执行** (`workflow.py`)
   - 创建 LangGraph StateGraph
   - 编译工作流
   - 执行工作流（传入初始状态）

3. **子智能体执行** (`agents.py`)
   - 每个节点创建 LangChain agent
   - 调用工具完成任务
   - 返回结构化输出
   - 更新状态

4. **路由决策** (`workflow.py`)
   - `should_continue_verification` 判断下一步
   - 返回 "error_repair" 或 "end"

5. **日志输出** (`callbacks.py`, `logging_utils.py`)
   - 控制台显示用户友好信息
   - 文件记录完整调试信息

## 关键设计决策

1. **确定性路由**: `should_continue_verification` 不使用 LLM，纯逻辑判断
2. **结构化输出**: 所有子智能体返回 Pydantic 模型，避免自由文本解析
3. **沙盒文件操作**: `save_text_file` 强制在 OUTPUT_ROOT 内
4. **双层日志**: 控制台（可配置）+ 文件（始终 DEBUG）
5. **迭代限制**: 最大迭代次数防止无限循环

## 扩展指南

### 添加新的子智能体

1. 在 `schemas.py` 定义 Pydantic 模型
2. 在 `prompts.py` 定义系统提示词
3. 在 `agents.py` 创建节点函数
4. 在 `workflow.py` 注册节点和边
5. 在 `should_continue_verification` 添加路由逻辑（如果需要）

### 添加新的工具

1. 在 `tools/` 下创建新文件
2. 实现工具函数（带类型注解和 docstring）
3. 在相关节点函数中添加到工具列表

## 调试技巧

1. **启用调试日志**: `--log-level debug`
2. **查看工作流可视化**: 使用 LangGraph 的可视化工具
3. **检查状态传递**: 在节点函数中添加日志输出
4. **验证结构化输出**: 检查 Pydantic 模型是否正确解析

## 总结

混合架构结合了 LangGraph 和 LangChain 的优势：
- LangGraph 提供确定性的工作流控制和状态管理
- LangChain Agents 提供灵活的子智能体能力和工具集成
- 状态管理和路由逻辑清晰分离
- 易于调试、扩展和维护

这种架构特别适合需要严格流程控制但又要灵活子智能体的场景，如论文代码复现这类多阶段任务。