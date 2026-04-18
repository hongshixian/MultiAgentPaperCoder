# MultiAgentPaperCoder

一个基于多智能体的自动化论文代码复现工具，基于 LangChain 和 LangGraph 生态构建。

## 功能特性

- 📄 自动读取和解析 PDF 格式论文
- 🧠 理解论文中算法的主要实现逻辑
- 💻 根据规划生成可运行的 Python 代码
- ✅ 验证代码是否可正常运行（训练）
- 🔍 提供错误分析和修复建议

## Agent 架构

```
MultiAgentPaperCoder
└── LangGraph Workflow (工作流编排)
    ├── DocumentAnalysisAgent  # 文档分析智能体（合并PDF读取+算法分析）
    ├── CodeGenerationAgent   # 代码生成智能体（合并代码规划+代码生成）
    ├── CodeVerificationAgent # 代码验证智能体（合并代码验证+结果验证）
    └── ErrorRepairAgent     # 错误修复智能体
```

### Agent 详细说明

| Agent | 功能 | 核心工具 |
|-------|------|----------|
| DocumentAnalysisAgent | 读取PDF并分析算法 | PDFParser + LLM |
| CodeGenerationAgent | 设计代码结构并生成完整代码 | LLM |
| CodeVerificationAgent | 验证代码执行并评估结果 | CodeExecutor + LLM |
| ErrorRepairAgent | 分析错误并生成修复建议 | LLM |

## 技术栈

- **Python**: 3.12+
- **LLM编排**: LangGraph (用于状态管理和条件路由)
- **LLM接口**: LangChain (统一LLM调用)
- **大语言模型**: 
  - Claude API (支持)
  - 智谱AI GLM API (支持)
- **PDF解析**: PyPDF2 + pdfplumber
- **代码执行**: subprocess + conda环境隔离
- **资源监控**: psutil (可选）

## 快速开始

### 1. 环境准备

```bash
# 创建conda环境
conda create -n py12pt python=3.12
conda activate py12pt

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置

复制 `.env.example` 为 `.env` 并配置：

```bash
cp .env.example .env
```

#### 使用 Claude API

编辑 `.env` 文件：
```
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=your_api_key_here
CLAUDE_MODEL=claude-3-5-sonnet-20241022
```

#### 使用 智谱AI API

编辑 `.env` 文件：
```
LLM_PROVIDER=zhipu
ZHIPU_API_KEY=your_zhipu_api_key_here
ZHIPU_MODEL=glm-5
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4
```

### 3. 使用

```bash
# 基本用法
python -m src.main --pdf path/to/your/paper.pdf

# 指定输出目录
python -m src.main --pdf paper.pdf --output-dir ./my_output

# 指定conda环境
python -m src.main --pdf paper.pdf --conda-env py12pt

# 启用详细输出
python -m src.main --pdf paper.pdf --verbose
```

## 项目结构

```
MultiAgentPaperCoder/
├── docs/                   # 设计文档
│   ├── design.md           # 详细设计说明
│   └── code-architecture.md # 系统架构设计
├── src/                    # 源代码
│   ├── agents/             # Agent实现（4个核心Agent）
│   │   ├── base.py                 # Agent基类
│   │   ├── document_analysis_agent.py # 文档分析智能体
│   │   ├── code_generation_agent.py   # 代码生成智能体
│   │   ├── code_verification_agent.py # 代码验证智能体
│   │   ├── error_repair_agent.py   # 错误修复智能体
│   │   └── __init__.py             # Agent模块初始化
│   ├── graph/              # 工作流编排
│   │   ├── workflow.py           # LangGraph工作流
│   │   └── __init__.py           # 图模块初始化
│   ├── llms/               # LLM抽象层
│   │   ├── base.py               # LLM基类
│   │   ├── llm_client.py         # LLM客户端实现
│   │   └── __init__.py           # LLM模块初始化
│   ├── tools/              # 工具集
│   │   ├── llm_client.py         # LLM客户端（向后兼容）
│   │   ├── pdf_parser.py         # PDF解析器
│   │   ├── code_executor.py     # 代码执行器
│   │   └── __init__.py           # 工具模块初始化
│   ├── state/              # 状态管理
│   │   └── __init__.py           # PaperState定义和状态模块初始化
│   ├── prompts/            # 提示词模板（YAML格式）
│   │   ├── __init__.py           # 提示词管理器
│   │   ├── document_analysis.yaml # 文档分析提示词
│   │   ├── code_generation.yaml   # 代码生成提示词
│   │   ├── code_verification.yaml # 代码验证提示词
│   │   └── error_repair.yaml     # 错误修复提示词
│   ├── config.py            # 配置管理
│   └── main.py              # 主入口
├── test_cases/            # 测试用例
├── output/                # 输出目录
│   └── generated_code/   # 生成的代码
├── requirements.txt       # Python依赖
├── .env.example          # 配置示例
└── README.md
```

## 输出结果

执行完成后，系统会生成以下内容：

### 1. 生成的代码

在 `output/generated_code/` 目录下生成完整的代码项目：

```
output/generated_code/
├── main.py              # 主训练脚本
├── model.py             # 模型定义
├── data_loader.py       # 数据加载
├── config.py            # 配置文件
├── utils.py             # 工具函数
└── requirements.txt     # 依赖列表
```

### 2. 执行报告

系统会输出详细的执行报告，包括：

- 论文标题和基本信息
- 算法名称和类型
- 生成的文件列表
- 验证结果（成功/失败）
- 错误日志（如有）
）
- 修复建议（如有）

## 开发指南

### 运行测试

```bash
# 运行所有测试
pytest test_cases/

# 运行特定测试类别
pytest test_cases/unit/
pytest test_cases/integration/

# 运行特定测试文件
pytest test_cases/unit/test_basic_imports.py

# 运行测试并显示输出
pytest test_cases/ -v
```

### 添加新的Agent

1. 继承 `BaseAgent` 类
2. 实现 `__call__` 方法
3. 在 `workflow.py` 中注册为节点

```python
from src.agents.base import BaseAgent

class MyCustomAgent(BaseAgent):
    def __init__(self, config=None):
        super().__init__("MyCustomAgent", config)

    def __call__(self, state):
        # 处理逻辑
        return updated_state
```

### 自定义提示词

在 `src/prompts/` 目录下创建对应的 `.yaml` 文件：

```yaml
name: my_prompt
input_variables:
  - var1
  - var2
output_format:
  field: type
template: |
  Your prompt here with {var1} and {var2}
```

## 技术决策

### 为什么选择LangGraph？

LangGraph具有以下优势：
- 更成熟的生态系统
- 完整的文档和示例
- 更好的社区支持
- 灵活的状态管理和条件路由

### 为什么支持智谱AI？

- 为国内用户提供更好的访问体验
- 降低API调用成本
- 与OpenAI SDK兼容，易于集成
- 支持中文场景优化

### 架构分层

系统采用清晰的分层架构：
- **Agent层**: 负责高层次决策和协调
- **Tool/LLM层**: 提供具体的基础能力

这种设计使得职责划分清晰，易于维护和扩展。

## 注意事项

1. **API Key安全**: 请妥善保管你的API Key，不要提交到版本控制
2. **成本控制**: 每次处理论文都会调用LLM API，注意监控使用量和成本
3. **Conda环境**: 确保指定的conda环境存在并且Python版本为3.12+
4. **代码安全**: 生成的代码在隔离环境中运行，但建议审查生成的代码
5. **PDF格式**: 目前支持标准PDF格式，扫描版PDF可能需要额外处理
6. **配置简化**: 仅支持 `.env` 文件配置，不支持YAML配置

## 未来计划

- [ ] 支持更多LLM模型（GPT-4, LLaMA等）
- [ ] 添加更多代码模板和最佳实践
- [ ] 支持增量更新（只修改需要修改的文件）
- [ ] 添加Web界面
- [ ] 支持论文数据库集成
- [ ] 添加代码质量检查（静态分析、测试覆盖率）
- [ ] 优化大论文的Token使用量
- [ ] 添加流式输出支持

## 文档

- [设计文档](docs/design.md) - 详细的设计说明
- [架构文档](docs/code-architecture.md) - 系统架构设计

## 许可证

MIT License
