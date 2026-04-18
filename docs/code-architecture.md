# 代码架构设计和开发计划

## 概述

本文档描述 MultiAgentPaperCoder 项目的代码架构设计和开发计划，重点阐述基于 LangChain 和 LangGraph 生态的技术实现方案。

## 技术选型

### 核心框架

| 组件 | 技术选择 | 版本要求 | 选择理由 |
|------|----------|----------|----------|
| 智能体编排 | LangGraph | >=0.2.0 | 状态管理、条件路由、循环迭代支持 |
| LLM 接口 | LangChain | >=0.2.0 | 统一的模型接口、工具调用、记忆管理 |
| 大语言模型 | 智谱 AI GLM-4.7 | 最新版本 | 符合中文场景需求，Token 限制充足 |

### 辅助库

| 类别 | 技术选择 | 用途 |
|------|----------|------|
| PDF 解析 | PyPDF2, pdfplumber | PDF 文本提取和结构化 |
| 数据验证 | Pydantic | 配置和状态验证 |
| 环境管理 | python-dotenv | 配置加载 |
| 日志 | rich | 进度展示和日志输出 |

## 代码架构设计

### 目录结构

```
MultiAgentPaperCoder/
├── src/
│   ├── __init__.py
│   ├── main.py                 # CLI 入口
│   ├── config.py               # 配置管理
│   ├── agents/                 # Agent 实现
│   │   ├── __init__.py
│   │   ├── base.py            # Agent 基类
│   │   ├── document_analysis_agent.py    # 文档分析智能体
│   │   ├── code_generation_agent.py      # 代码生成智能体
│   │   ├── code_verification_agent.py     # 代码验证智能体
│   │   └── error_repair_agent.py         # 错误修复智能体
│   ├── graph/                  # 工作流编排
│   │   ├── __init__.py
│   │   └── workflow.py         # LangGraph 工作流
│   ├── state/                  # 状态管理
│   │   └── __init__.py
│   └── tools/                  # 工具层
│       ├── __init__.py
│       ├── pdf_reader.py       # PDF 解析工具
│       ├── llm_client.py       # LLM 客户端（基于 LangChain）
│       └── code_executor.py    # 代码执行器
│   └── prompts/                # 提示词管理
│       ├── __init__.py         # PromptManager
│       ├── document_analysis.yaml
│       ├── code_generation.yaml
│       ├── code_verification.yaml
│       └── error_repair.yaml
├── config/                    # 配置文件
│   └── default.yaml
├── test_cases/                # 测试用例
│   ├── unit/
│   └── integration/
├── docs/                      # 文档
├── output/                    # 输出目录
├── .env.example              # 环境变量示例
└── requirements.txt          # Python 依赖
```

### Agent 设计

所有 Agent 继承自统一的 `BaseAgent`，遵循 LangChain 的 Agent 模式。

```python
from typing import Dict, Any
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    @abstractmethod
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass
```

### LangGraph 工作流设计

使用 LangGraph 的 StateGraph 实现状态机模式：

```python
from langgraph.graph import StateGraph
from typing import TypedDict

class PaperState(TypedDict):
    pdf_path: str
    paper_content: Optional[Dict]
    algorithm_analysis: Optional[Dict]
    code_plan: Optional[Dict]
    generated_code: Optional[Dict]
    verification_result: Optional[Dict]
    repair_history: List[Dict]
    current_step: str
    errors: List[str]
    iteration_count: int
    max_iterations: int

# 创建 LangGraph 工作流
workflow = StateGraph(PaperState)

# 添加节点和边
workflow.add_node("文档分析", document_analysis_node)
workflow.add_node("代码生成", code_generation_node)
workflow.add_node("代码验证", code_verification_node)
workflow.add_node("错误修复", error_repair_node)

# 添加条件路由
workflow.add_conditional_edges(
    "代码验证",
    should_continue,
    {
        "需要修复": "错误修复",
        "完成": END
    }
)

workflow.set_entry_point("文档分析")
```

### LLM 客户端设计（基于 LangChain）

使用 LangChain 的 Chat 接口实现统一的 LLM 调用：

```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

class LLMClient:
    def __init__(self, config: Dict = None):
        self.llm = ChatOpenAI(
            model=config.get("model", "glm-4.7"),
            api_key=config.get("api_key", os.getenv("ZHIPU_API_KEY", "")),
            base_url=config.get("base_url", "https://open.bigmodel.cn/api/paas/v4"),
            max_tokens=config.get("max_tokens", 128000),
            temperature=config.get("temperature", 0.7),
        )

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))
        response = self.llm.invoke(messages)
        return response.content

    def generate_structured(self, prompt: str, output_format: Dict = None) -> Dict:
        # 使用 LangChain 的 with_structured_output
        from langchain.output_parsers import PydanticOutputParser
        # ... 实现
```

## 开发计划

### 第一阶段：核心框架搭建

**目标**：完成基础架构和工作流实现

#### 1.1 状态管理（State Management）
- [ ] 实现 `PaperState` TypedDict
- [ ] 添加状态验证和序列化支持
- [ ] 实现状态持久化（可选）

#### 1.2 基础 Agent 实现
- [ ] 实现 `BaseAgent` 抽象基类
- [ ] 实现各子 Agent 的基本框架
- [ ] 添加单元测试

#### 1.3 LangGraph 工作流集成
- [ ] 使用 LangGraph 重构现有工作流
- [ ] 实现条件路由
- [ ] 添加循环迭代支持
- [ ] 添加状态持久化

**时间估算**：2 周

### 第二阶段：Agent 功能实现

**目标**：完成各 Agent 的具体业务逻辑

#### 2.1 文档分析智能体
- [ ] 集成 PDF 解析工具
- [ ] 实现算法分析逻辑（基于 LLM）
- [ ] 添加结构化输出支持
- [ ] 实现公式和图表提取（可选）

#### 2.2 代码生成智能体
- [ ] 实现代码规划功能
- [ ] 实现代码生成功能（基于 LLM）
- [ ] 实现依赖分析
- [ ] 添加配置文件生成

#### 2.3 代码验证智能体
- [ ] 集成代码执行工具
- [ ] 实现代码监控和日志记录
- [ ] 实现错误收集和分析
- [ ] 实现结果对比和评估

#### 2.4 错误修复智能体
- [ ] 实现错误分析和定位
- [ ] 实现代码修复逻辑
- [ ] 实现修复验证

**时间估算**：3 周

### 第三阶段：工具层完善

**目标**：完善 Tool 层的实现

#### 3.1 LLM 客户端（基于 LangChain）
- [ ] 使用 LangChain Chat 接口重构
- [ ] 添加流式输出支持
- [ ] 添加结构化输出解析器
- [ ] 添加重试机制和错误处理
- [ ] 添加 Token 统计

#### 3.2 PDF 解析工具
- [ ] 优化 PDF 解析准确率
- [ ] 添加章节结构识别
- [ ] 添加表格解析支持

#### 3.3 代码执行工具
- [ ] 改进错误捕获和报告
- [ ] 添加资源监控（CPU、内存）
- [ ] 添加超时控制

**时间估算**：2 周

### 第四阶段：提示词优化

**目标**：优化各 Agent 的提示词模板

#### 4.1 提示词模板迁移
- [ ] 将 TXT 格式提示词迁移到 YAML 格式
- [ ] 添加元数据和输入变量定义
- [ ] 实现 PromptManager

#### 4.2 提示词调优
- [ ] 设计提示词 A/B 测试框架
- [ ] 优化算法分析提示词
- [ ] 优化代码生成提示词
- [ ] 优化错误修复提示词
- [ ] 优化结果验证提示词

**时间估算**：2 周

### 第五阶段：测试和优化

**目标**：完善测试覆盖率和性能优化

#### 5.1 单元测试
- [ ] 完成 Agent 基类测试
- [ ] 完成各 Agent 单元测试
- [ ] 完成工具层单元测试
- [ ] 达到 80% 以上覆盖率

#### 5.2 集成测试
- [ ] 编写端到端工作流测试
- [ ] 添加 PDF 处理集成测试
- [ ] 添加代码生成集成测试
- [ ] 添加错误修复集成测试

#### 5.3 性能优化
- [ ] LLM 调用缓存
- [ ] 并行化独立任务
- [ ] 优化内存使用
- [ ] 添加性能监控

**时间估算**：2 周

## 技术债务和未来改进

### 当前技术债务

1. **LangGraph 集成不完整**：当前工作流是自定义实现，未充分利用 LangGraph 的状态管理和路由能力
2. **提示词格式混乱**：同时存在 YAML 和 TXT 两种格式，需要统一
3. **错误处理不一致**：各 Agent 的错误处理逻辑不统一
4. **测试覆盖率不足**：当前测试覆盖率较低

### 未来改进方向

1. **完全采用 LangGraph 生态**
   - 使用 LangGraph 的 StateGraph 替代自定义工作流
   - 利用 LangGraph 的可视化工具调试工作流
   - 使用 LangGraph 的持久化功能

2. **统一提示词系统**
   - 完全迁移到 YAML 格式
   - 添加提示词版本管理
   - 支持提示词热更新

3. **增强 Tool 层能力**
   - 添加更多 PDF 解析特性（公式 OCR、表格解析）
   - 添加代码静态分析工具
   - 添加代码格式化工具

4. **提升可观测性**
   - 添加分布式追踪（如 OpenTelemetry）
   - 添加性能监控面板
   - 添加日志聚合和分析

5. **扩展多 LLM 支持**
   - 使用 LangChain 的多模型支持
   - 添加 Claude、OpenAI 等模型支持
   - 实现模型路由和负载均衡

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
3. Pull Request 审查：至少一人审核
4. 持续集成：自动化测试和代码检查

## 总结

本文档基于 LangChain 和 LangGraph 生态系统，阐述了 MultiAgentPaperCoder 的代码架构设计和开发计划。通过分阶段的开发计划，确保系统架构清晰、可维护、可扩展。技术债务的识别和未来改进方向的规划，为项目的长期发展提供了明确的路线图。
