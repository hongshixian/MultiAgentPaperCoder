# 代码架构设计和实现

## 概述

本文档描述 MultiAgentPaperCoder 项目的代码架构设计和当前实现，重点阐述基于 LangGraph 工作流编排和 LangChain 子智能体（类 deepagents）的混合技术方案。

## 技术选型

### 核心框架

| 组件 | 技术选择 | 版本要求 | 选择理由 |
|------|----------|----------|----------|
| 工作流编排 | LangGraph | >=1.1.0 | 状态管理、条件路由、循环迭代支持 |
| 子智能体框架 | LangChain Agents | >=0.2.0 | 工具调用、结构化输出、回调机制 |
| 大语言模型 | 智谱 AI GLM-4.7 (OpenAI 兼容 API) | 最新版本 | 符合中文场景需求，Token 限制充足 |

### 辅助库

| 类别 | 技术选择 | 用途 |
|------|----------|------|
| PDF 解析 | PyPDF2 | PDF 文本提取和结构化 |
| 数据验证 | Pydantic | 配置、状态和结构化输出验证 |
| 环境管理 | python-dotenv | 配置加载 |

## 代码架构设计

### 目录结构

```
MultiAgentPaperCoder/
├── src/
│   ├── __init__.py
│   ├── hybrid/                 # 混合架构实现
│   │   ├── __init__.py
│   │   ├── main.py            # CLI 入口
│   │   ├── config.py          # 配置管理（Settings, LLM 构建）
│   │   ├── agents.py          # LangGraph 节点函数（4个子智能体）
│   │   ├── workflow.py        # LangGraph StateGraph 工作流
│   │   ├── state.py           # PaperState TypedDict
│   │   ├── schemas.py         # Pydantic 结构化输出模型
│   │   ├── prompts.py         # 子智能体系统提示词
│   │   ├── logging_utils.py   # 日志配置和文件日志器
│   │   ├── callbacks.py       # LangChain 回调处理器
│   │   └── tools/             # 工具层
│   │       ├── __init__.py
│   │       ├── pdf_tools.py       # PDF 解析工具
│   │       ├── artifact_tools.py  # 文件读写工具（沙盒限制）
│   │       └── exec_tools.py      # 代码执行工具
├── test_cases/                # 测试用例
│   ├── unit/
│   │   └── test_hybrid.py    # 混合实现测试
│   └── integration/
├── docs/                      # 文档
├── output/                    # 输出目录
├── .env.example              # 环境变量示例
└── requirements.txt          # Python 依赖
```

### 混合架构设计

MultiAgentPaperCoder 采用**混合架构**，结合了两种框架的优势：

1. **LangGraph**: 用于确定性的工作流编排和状态管理
   - StateGraph 状态机
   - 条件路由
   - 迭代循环

2. **LangChain Agents**: 用于子智能体专业化
   - 工具调用
   - 结构化输出
   - 回调机制

```
┌─────────────────────────────────────────────────────────┐
│                   CLI Layer (main.py)                    │
│  ┌───────────────────────────────────────────────────┐  │
│  │  参数解析、日志配置 (setup_console_logging)      │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│              LangGraph Workflow Layer                    │
│  ┌───────────────────────────────────────────────────┐  │
│  │  StateGraph: 4 nodes + conditional routing       │  │
│  │  should_continue_verification() 纯逻辑路由         │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│              Sub-Agent Nodes (agents.py)                 │
│  ┌──────────────────┐  ┌────────────────┐  ┌──────────────┐  │
│  │ document-analyst │  │ code-generator │  │ code-verifier │  │
│  │  create_agent()  │  │  create_agent()│  │create_agent() │  │
│  └──────────────────┘  └────────────────┘  └──────────────┘  │
│  ┌──────────────────────────────────────────────┐           │
│  │            error-repairer                    │           │
│  │            create_agent()                    │           │
│  └──────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                   Tool Layer (tools/)                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────┐  │
│  │   pdf_tools      │  │  artifact_tools  │  │ exec_  │  │
│  │   read_pdf_text  │  │  save/read/list  │  │ tools  │  │
│  └──────────────────┘  └──────────────────┘  └────────┘  │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│              LLM Layer (config.py)                       │
│  ┌───────────────────────────────────────────────────┐  │
│  │   ChatOpenAI (OpenAI-compatible API)              │  │
│  │   支持 ZhipuAI 等兼容服务                          │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 子智能体节点设计

每个节点在 `src/hybrid/agents.py` 中实现，创建 LangChain agent 并返回结构化输出：

```python
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from .callbacks import PapercoderCallbackHandler
from .schemas import MyAgentResult

def my_agent_node(state: PaperState, config: dict) -> dict:
    settings: Settings = config["settings"]
    
    agent = create_agent(
        model=settings.build_llm(),
        tools=[/* 相关工具 */],
        system_prompt=MY_AGENT_PROMPT,
        response_format=MyAgentResult,  # Pydantic 结构化输出
        name="my-agent",
    )
    
    result = agent.invoke(
        {"messages": [HumanMessage(content="Your prompt")]},
        config={"callbacks": [PapercoderCallbackHandler()]},  # 结构化日志
    )
    
    structured = _extract_structured(result)
    return { /* 状态更新 */ }
```

### LangGraph 工作流设计

使用 LangGraph 的 StateGraph 实现状态机模式：

```python
from langgraph.graph import StateGraph, END

class PaperState(TypedDict, total=False):
    # 输入
    pdf_path: str
    
    # 文档分析结果
    analysis_path: str
    analysis_status: str  # "completed" or "failed"
    
    # 代码生成结果
    code_dir: str
    file_list: list[str]
    generation_status: str  # "completed" or "failed"
    
    # 验证结果
    verification_passed: bool
    error_type: str  # "none", "import_error", "runtime_error", "logic_error"
    error_cause: str
    error_location: str
    stdout_summary: str
    needs_repair: bool
    
    # 错误修复结果
    repair_status: str  # "completed" or "failed"
    files_modified: list[str]
    
    # 控制字段
    iteration_count: int
    max_iterations: int
    errors: list[str]

def should_continue_verification(state: PaperState) -> str:
    """确定性路由逻辑，无 LLM 参与"""
    if state.get("analysis_status") != "completed":
        return "end"
    if state.get("generation_status") != "completed":
        return "end"
    if not state.get("needs_repair", False):
        return "end"
    if state.get("iteration_count", 0) >= state.get("max_iterations", 5):
        return "end"
    return "error_repair"

# 创建 LangGraph 工作流
workflow = StateGraph(PaperState)

# 添加节点
workflow.add_node("document_analysis", document_analysis_node)
workflow.add_node("code_generation", code_generation_node)
workflow.add_node("code_verification", code_verification_node)
workflow.add_node("error_repair", error_repair_node)

# 添加边
workflow.set_entry_point("document_analysis")
workflow.add_edge("document_analysis", "code_generation")
workflow.add_edge("code_generation", "code_verification")
workflow.add_conditional_edges(
    "code_verification",
    should_continue_verification,
    {"error_repair": "error_repair", "end": END},
)
workflow.add_edge("error_repair", "code_verification")
```

### LLM 客户端设计（基于 LangChain ChatOpenAI）

使用 LangChain 的 ChatOpenAI 实现 OpenAI 兼容的 LLM 调用：

```python
from langchain_openai import ChatOpenAI

class Settings:
    @property
    def resolved_model_name(self) -> str:
        """标准化模型名称，移除提供商前缀"""
        if ":" in self.model_name:
            _, model = self.model_name.split(":", 1)
            return model
        return self.model_name
    
    def build_llm(self):
        """创建 OpenAI 兼容的 LangChain Chat 模型
        
        支持通过设置 base_url 使用 ZhipuAI 等兼容服务
        """
        kwargs = {
            "model": self.resolved_model_name,
            "api_key": self.openai_api_key,
        }
        if self.openai_base_url:
            kwargs["base_url"] = self.openai_base_url
        return ChatOpenAI(**kwargs)
```

### 日志系统设计

系统实现双层日志架构：

1. **控制台日志** (`src/hybrid/logging_utils.py`):
   - 由 `--log-level` CLI 参数控制
   - `info`: 显示 agent/node/tool 调用
   - `debug`: 额外显示 LLM 请求/响应

2. **结构化回调** (`src/hybrid/callbacks.py`):
   - `PapercoderCallbackHandler` 捕获 LangChain 事件
   - INFO: "Agent正在思考...", "Agent调用了工具: xx"
   - DEBUG: LLM 请求提示词和响应内容

3. **文件日志**:
   - 写入 `{run_dir}/logs/papercoder_{timestamp}.log`
   - 文件日志始终为 DEBUG 级别

## 当前实现状态

### 已完成模块

#### ✅ 核心框架（第一阶段完成）
- [x] 实现 `PaperState` TypedDict（`src/hybrid/state.py`）
- [x] 实现 4 个子智能体节点函数（`src/hybrid/agents.py`）
- [x] 实现 LangGraph StateGraph 工作流（`src/hybrid/workflow.py`）
- [x] 实现确定性路由逻辑（`should_continue_verification`）
- [x] 实现 Pydantic 结构化输出模型（`src/hybrid/schemas.py`）
- [x] 实现 CLI 入口（`src/hybrid/main.py`）
- [x] 实现配置管理（`src/hybrid/config.py`）

#### ✅ 子智能体功能（第二阶段完成）
- [x] 文档分析智能体（document-analyst）: PDF 解析 + 结构化分析
- [x] 代码生成智能体（code-generator）: 基于分析生成 Python 项目
- [x] 代码验证智能体（code-verifier）: 安装依赖 + 执行代码 + 验证输出
- [x] 错误修复智能体（error-repairer）: 分析错误 + 修复代码

#### ✅ 工具层（第三阶段完成）
- [x] PDF 工具（`pdf_tools.py`）: `read_pdf_text`
- [x] 工件工具（`artifact_tools.py`）: `save_text_file`, `read_text_file`, `list_files`（带沙盒限制）
- [x] 执行工具（`exec_tools.py`）: `python_syntax_check`, `check_entrypoint_exists`, `install_requirements`, `run_python_entrypoint`

#### ✅ 日志和可观测性（近期完成）
- [x] 控制台日志配置（`setup_console_logging`）
- [x] 文件日志器（`create_run_logger`）
- [x] LangChain 回调处理器（`PapercoderCallbackHandler`）
- [x] 工作流节点流转日志（中文）
- [x] `--log-level` CLI 参数

#### ✅ 测试覆盖（进行中）
- [x] 路由逻辑测试（`TestRouter`）
- [x] 状态字段测试（`TestPaperState`）
- [x] Pydantic schema 测试（`TestSchemas`）
- [x] 工具测试（`TestArtifactTools`, `TestExecTools`）
- [x] 配置测试（`TestSettings`）
- [x] 工作流构建测试（`TestWorkflowBuild`）

### 待完成功能

#### ⏳ 增强验证能力
- [ ] 真实训练脚本执行（当前仅为语法检查和入口点验证）
- [ ] 结果指标对比和评估
- [ ] 资源使用监控（CPU、内存）

#### ⏳ 提示词优化
- [ ] 基于真实论文调优各子智能体提示词
- [ ] 添加提示词版本管理
- [ ] 提示词 A/B 测试框架

#### ⏳ 其他改进
- [ ] 添加更多 PDF 解析特性（公式 OCR、表格解析）
- [ ] 添加代码静态分析工具
- [ ] 添加分布式追踪（OpenTelemetry）
- [ ] 添加性能监控面板

## 技术债务和未来改进

### 当前技术债务

1. **验证能力有限**: 当前仅为语法检查和入口点验证，未实现真实训练执行
2. **错误类型分类不够细致**: 当前只有 4 种错误类型，可能需要更细粒度分类
3. **测试覆盖率有待提高**: 需要更多集成测试和端到端测试

### 未来改进方向

1. **增强验证能力**
   - 实现真实训练脚本执行
   - 添加结果指标对比
   - 添加训练过程监控

2. **提升可观测性**
   - 添加分布式追踪
   - 添加性能监控
   - 添加日志聚合

3. **扩展多 LLM 支持**
   - 支持 Anthropic Claude
   - 支持 OpenAI GPT
   - 实现模型路由和负载均衡

4. **改进代码修复**
   - 更智能的错误分类
   - 更精准的修复策略
   - 修复效果评估

## 代码规范

### Python 代码规范

1. 遵循 PEP 8 编码规范
2. 使用类型注解（Type hints）
3. 编写 docstring 文档
4. 使用有意义的变量和函数命名
5. 保持函数单一职责

### Git 工作流

1. 分支策略：feature 分支开发，合并到 main
2. 提交信息规范：使用约定式提交
3. 持续集成：自动化测试

## 总结

MultiAgentPaperCoder 项目采用 LangGraph 和 LangChain 的混合架构，实现了论文代码复现的自动化流程。核心架构已完成，包括工作流编排、子智能体实现、工具层和日志系统。未来将重点增强验证能力和提升可观测性。
