# MultiAgentPaperCoder 代码重构计划

## 概述

本文档基于对《项目设计Document毕业论文参考.md》、`docs/design.md` 和 `docs/code-architecture.md` 三份设计文档的审阅，对照当前代码实际状态，梳理出设计目标与实现现状之间的差距，并制定分阶段的重构计划。

重构的核心原则：**先修复阻断性问题（运行时错误），再消除架构冗余，最后补齐缺失功能**。

---

## 现状分析：设计与实现的差距

### 1. 代码可运行性问题（阻断性）

当前代码存在以下导致运行时崩溃的问题：

| 问题 | 位置 | 影响 |
|------|------|------|
| Prompt 模板名称不匹配 | Agent 引用的模板名与 YAML 文件定义的 name 不一致 | 运行时 KeyError 崩溃 |
| LLM Client 导入路径错误 | 所有 Agent 从 `src/tools/llm_client.py` 导入，该文件未继承 BaseLLM | 架构不一致 |
| 缺少部分 Prompt YAML 文件 | Agent 引用的模板无对应 YAML 文件 | 运行时 KeyError |

**具体模板名称不匹配详情：**

| Agent 文件 | 引用的模板名 | YAML 文件中的 name 字段 | 状态 |
|------------|-------------|----------------------|------|
| `document_analysis_agent.py:110` | `algorithm_analyzer` | `document_analysis` | 不匹配 |
| `code_generation_agent.py:102` | `code_planner` | 无对应文件 | 缺失 |
| `code_generation_agent.py:168` | `code_generator` | `code_generation`（name 字段一致但文件内容不同） | 需确认 |
| `code_verification_agent.py:160` | `result_verification` | `code_verification` | 不匹配 |
| `error_repair_agent.py:63` | `error_repair` | `error_repair` | 匹配 |

### 2. 架构冗余问题

| 问题 | 详情 |
|------|------|
| LLM Client 重复实现 | `src/tools/llm_client.py` 和 `src/llms/llm_client.py` 几乎完全相同，前者未继承 BaseLLM，后者正确继承 |
| State 字段 `env_config` 未使用 | `PaperState` 定义了 `env_config` 字段，但无任何 Agent 写入或读取 |
| 设计文档引用不存在的文件 | `docs/design.md` 引用 `pdf_reader.py`、`algorithm_analyzer.py`、`code_planner.py` 等已不存在的文件路径 |

### 3. 功能缺失

| 缺失功能 | 设计文档中的要求 | 当前状态 |
|----------|-----------------|---------|
| 测试用例 | 代码架构文档要求 80% 以上覆盖率 | `test_cases/` 目录为空，仅有 `__init__.py` |
| 用户界面层 | 论文要求 Streamlit 前端界面 | 无任何前端实现 |
| Docker 环境支持 | 论文要求生成 Docker 构建脚本 | 无相关实现 |
| Prompt TXT 遗留格式 | 设计文档提到 TXT 格式向后兼容 | `PromptManager` 不再加载 TXT 文件 |
| 领域知识库 | 架构图中 Tool 层包含知识库 | 无实现 |

---

## 重构计划

### 第一阶段：修复阻断性问题（优先级：紧急）

> 目标：让系统能够正常运行，不出现运行时崩溃

#### 1.1 统一 Prompt 模板名称

**问题**：Agent 代码中引用的模板名与 YAML 文件中定义的 `name` 字段不一致。

**方案**：修改 YAML 文件的 `name` 字段和 `input_variables` 以匹配 Agent 的调用，同时补齐缺失的模板。

**具体操作**：

- **`src/prompts/document_analysis.yaml`**：将 `name: document_analysis` 改为 `name: algorithm_analyzer`，匹配 `DocumentAnalysisAgent` 中的调用 `PROMPTS.format_template("algorithm_analyzer", ...)`
- **新建 `src/prompts/code_planner.yaml`**：创建代码规划专用模板，`name: code_planner`，匹配 `CodeGenerationAgent._plan_code()` 中的调用
- **`src/prompts/code_generation.yaml`**：确认 `name: code_generator`，匹配 `CodeGenerationAgent._generate_code()` 中的调用 `PROMPTS.format_template("code_generator", ...)`
- **`src/prompts/code_verification.yaml`**：将 `name: code_verification` 改为 `name: result_verification`，匹配 `CodeVerificationAgent._verify_results()` 中的调用 `PROMPTS.format_template("result_verification", ...)`

**涉及文件**：
- `src/prompts/document_analysis.yaml`
- `src/prompts/code_generation.yaml`
- `src/prompts/code_verification.yaml`
- `src/prompts/code_planner.yaml`（新建）

#### 1.2 消除 LLM Client 重复

**问题**：`src/tools/llm_client.py` 和 `src/llms/llm_client.py` 存在重复代码。所有 Agent 从 `src/tools/llm_client.py` 导入 LLMClient，但该文件未继承 BaseLLM 抽象基类，不符合设计规范。`src/llms/llm_client.py` 是正确的实现，继承了 BaseLLM。

**方案**：删除 `src/tools/llm_client.py`，将所有 Agent 的导入改为从 `src/llms/llm_client.py` 导入。

**涉及文件**：
- `src/agents/document_analysis_agent.py` — 将 `from ..tools.llm_client import LLMClient` 改为 `from ..llms.llm_client import LLMClient`
- `src/agents/code_generation_agent.py` — 同上
- `src/agents/code_verification_agent.py` — 同上
- `src/agents/error_repair_agent.py` — 同上
- `src/tools/llm_client.py` — 删除

#### 1.3 清理未使用的 State 字段

**问题**：`PaperState` 中的 `env_config` 字段无任何 Agent 使用。

**方案**：移除 `env_config` 字段，保持 State 定义精简。如果未来需要环境配置功能，再按需添加。

**涉及文件**：
- `src/state/__init__.py`

---

### 第二阶段：架构优化（优先级：高）

> 目标：消除代码冗余，提高代码质量和一致性

#### 2.1 统一 Agent 配置传递

**问题**：`workflow.py` 中创建 Agent 时未传递全局 config，各 Agent 各自初始化默认配置。

**方案**：在 `PaperCoderWorkflow` 中统一管理配置，创建 Agent 时传入配置。

**具体操作**：
- `workflow.py` 中的 node 函数从闭包或全局获取 config，传递给 Agent 构造函数
- 各 Agent 构造函数接受 config 参数并使用其中的 output_dir、conda_env_name 等配置

**涉及文件**：
- `src/graph/workflow.py`
- `src/agents/document_analysis_agent.py`
- `src/agents/code_generation_agent.py`
- `src/agents/code_verification_agent.py`
- `src/agents/error_repair_agent.py`

#### 2.2 增强错误处理一致性

**问题**：各 Agent 的错误处理模式不完全一致，有的返回 errors 列表，有的直接抛异常。

**方案**：在 BaseAgent 中提供统一的错误处理辅助方法。

```python
# 在 BaseAgent 中添加
def _error_state(self, state: Dict[str, Any], message: str) -> Dict[str, Any]:
    """Return state with appended error message."""
    errors = state.get("errors", []) + [f"[{self.name}] {message}"]
    return {**state, "errors": errors}

def _success_state(self, state: Dict[str, Any], updates: Dict[str, Any], step: str) -> Dict[str, Any]:
    """Return state with updates and current_step set."""
    return {**state, **updates, "current_step": step}
```

**涉及文件**：
- `src/agents/base.py`
- 各 Agent 文件（使用统一方法替换各自的错误处理模式）

#### 2.3 移除 Agent 中硬编码的 system_prompt

**问题**：各 Agent 内部硬编码了 system_prompt 字符串，未利用 Prompt 系统管理。

**方案**：将硬编码的 system_prompt 移入 YAML 模板的元数据中，或添加为 YAML 的 `system_prompt` 字段，Agent 从模板获取。

**涉及文件**：
- `src/prompts/*.yaml`（添加 `system_prompt` 字段）
- `src/prompts/__init__.py`（PromptTemplate 支持 system_prompt）
- 各 Agent 文件（移除硬编码的 system_prompt）

#### 2.4 更新设计文档中的文件引用

**问题**：`docs/design.md` 中引用了不存在的文件路径。

**方案**：更新 `docs/design.md` 中的 Agent 实现文件路径，使其与当前代码一致。

**需要更新的引用**：
| 设计文档中的路径 | 实际路径 |
|-----------------|---------|
| `src/agents/pdf_reader.py` | 不存在（功能合并入 `document_analysis_agent.py`） |
| `src/agents/algorithm_analyzer.py` | 不存在（功能合并入 `document_analysis_agent.py`） |
| `src/agents/code_planner.py` | 不存在（功能合并入 `code_generation_agent.py`） |
| `src/agents/code_generator.py` | 不存在（功能合并入 `code_generation_agent.py`） |
| `src/agents/code_validator.py` | 不存在（功能合并入 `code_verification_agent.py`） |
| `src/agents/result_verification_agent.py` | 不存在（功能合并入 `code_verification_agent.py`） |
| `src/tools/pdf_reader.py` | 实际为 `src/tools/pdf_parser.py` |
| `src/agents/super_agent.py` | 不存在（功能由 `src/graph/workflow.py` 的 PaperCoderWorkflow 承担） |

**涉及文件**：
- `docs/design.md`

---

### 第三阶段：补齐测试（优先级：高）

> 目标：建立测试基础设施，覆盖核心逻辑

#### 3.1 单元测试

**测试范围和优先级**：

| 优先级 | 测试对象 | 测试内容 |
|--------|---------|---------|
| P0 | `src/config.py` | 配置加载、验证、默认值 |
| P0 | `src/state/__init__.py` | PaperState 结构完整性 |
| P0 | `src/prompts/__init__.py` | 模板加载、格式化、缺失变量检测 |
| P1 | `src/llms/llm_client.py` | JSON 解析（直接、代码块、尾随逗号）、get_llm 工厂函数 |
| P1 | `src/tools/pdf_parser.py` | PDF 解析（使用 mock 或测试 PDF） |
| P1 | `src/tools/code_executor.py` | 代码执行、超时、错误捕获 |
| P2 | `src/agents/base.py` | BaseAgent 抽象行为 |
| P2 | 各 Agent | 使用 mock LLM 测试 Agent 的状态流转 |

**测试目录结构**：

```
test_cases/
├── __init__.py
├── unit/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_state.py
│   ├── test_prompt_manager.py
│   ├── test_llm_client.py
│   ├── test_pdf_parser.py
│   └── test_code_executor.py
└── integration/
    ├── __init__.py
    └── test_workflow.py
```

#### 3.2 集成测试

- 端到端工作流测试（使用 mock LLM）
- 条件路由测试（should_continue_verification 逻辑分支覆盖）
- 迭代修复循环测试

---

### 第四阶段：功能完善（优先级：中）

> 目标：补齐设计文档中规划但尚未实现的功能

#### 4.1 代码生成输出路径改进

**问题**：当前 `CodeGenerationAgent` 使用固定的 `output_dir`，多次运行会覆盖之前的结果。

**方案**：参考 `src/config.py` 中已有的时间戳 + PDF 文件名的目录生成逻辑，在 Agent 中使用。

**涉及文件**：
- `src/agents/code_generation_agent.py`
- `src/graph/workflow.py`

#### 4.2 添加日志系统

**问题**：当前使用 `print()` 输出状态信息，缺乏结构化日志。

**方案**：引入 Python 标准 `logging` 模块，配合 `rich` 库进行格式化输出，替换所有 `print()` 调用。

**涉及文件**：
- 新建 `src/utils/logger.py`（日志配置模块）
- `src/graph/workflow.py`
- 各 Agent 文件

#### 4.3 Prompt 模板补充

**问题**：当前缺少 `code_planner.yaml`、`env_config.yaml` 等设计文档中提到的模板。

**方案**：
- 新建 `src/prompts/code_planner.yaml`（代码规划提示词）
- 新建 `src/prompts/env_config.yaml`（环境配置提示词）
- 评估是否需要 `algorithm_analyzer.yaml`（与 document_analysis 合并或独立）

**涉及文件**：
- `src/prompts/code_planner.yaml`（新建）
- `src/prompts/env_config.yaml`（新建）

---

### 第五阶段：文档和代码一致性（优先级：中低）

> 目标：确保文档准确反映代码实现

#### 5.1 更新 CLAUDE.md

**问题**：CLAUDE.md 中列出的 Prompt 模板文件名与实际不一致。

**需要更新**：
- CLAUDE.md 中 "Prompt Templates" 部分列出的模板文件名
- 更新架构图中的 "LangGraph 工作流" 描述（当前未体现"超级智能体"概念）

#### 5.2 更新 docs/code-architecture.md

**问题**：开发计划中的复选框状态需要更新，反映已完成的和未完成的工作。

**需要更新**：
- 标记已完成的开发任务
- 更新技术债务列表
- 更新目录结构图

#### 5.3 更新 docs/design.md

**问题**：如 2.4 节所述，文件路径引用过时。

---

## 重构优先级总览

```
第一阶段（紧急）          第二阶段（高）           第三阶段（高）
┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐
│ 1.1 统一模板名称   │   │ 2.1 统一配置传递   │   │ 3.1 单元测试       │
│ 1.2 消除LLM重复    │   │ 2.2 统一错误处理   │   │ 3.2 集成测试       │
│ 1.3 清理State字段  │   │ 2.3 移除硬编码提示 │   │                   │
└───────────────────┘   │ 2.4 更新文档引用   │   └───────────────────┘
                        └───────────────────┘
第四阶段（中）            第五阶段（中低）
┌───────────────────┐   ┌───────────────────┐
│ 4.1 输出路径改进   │   │ 5.1 更新CLAUDE.md  │
│ 4.2 日志系统      │   │ 5.2 更新架构文档   │
│ 4.3 补齐Prompt模板│   │ 5.3 更新设计文档   │
└───────────────────┘   └───────────────────┘
```

## 实施建议

1. **每阶段独立提交**：每个阶段完成后创建独立 commit，便于回滚和追踪
2. **第一阶段完成后立即验证**：修复阻断性问题后，使用一个测试 PDF 验证端到端流程
3. **第二阶段与第三阶段可并行**：架构优化和测试编写可以同时进行
4. **第四、五阶段按需推进**：根据实际使用情况决定优先级

## 不在本次重构范围内的事项

以下功能在设计文档中提及，但涉及较大工作量，建议作为独立项目推进：

- Streamlit 用户界面（论文中描述的用户界面层）
- Docker 容器化支持（论文中描述的隔离执行环境）
- 领域知识库（架构图中的 Tool 层组件）
- 多 LLM 负载均衡
- 分布式追踪（OpenTelemetry）
- 提示词 A/B 测试框架
