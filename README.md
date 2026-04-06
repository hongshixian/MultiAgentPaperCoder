# MultiAgentPaperCoder

一个基于多智能体的自动化论文代码复现工具。

## 功能特性

- 📄 自动读取和解析PDF格式论文
- 🧠 理解论文中算法的主要实现逻辑
- 📋 规划如何复现论文代码
- 💻 根据规划生成可运行的Python代码
- ✅ 验证代码是否可正常运行（训练）
- 🔍 提供错误分析和修复建议

## Agent 架构

```
MultiAgentPaperCoder
└── PaperCoderSuperAgent (主控智能体)
    ├── PDFReaderAgent      # 论文读取器
    ├── AlgorithmAnalyzerAgent  # 算法分析器
    ├── CodePlannerAgent     # 代码规划器
    ├── CodeGeneratorAgent   # 代码生成器
    └── CodeValidatorAgent   # 代码验证器
```

### Agent 详细说明

| Agent | 功能 | 核心工具 |
|-------|------|----------|
| PaperCoderSuperAgent | 协调工作流和状态管理 | LangGraph工作流 |
| PDFReaderAgent |.读取PDF并提取结构化内容 | PyPDF2/pdfplumber |
| AlgorithmAnalyzerAgent | 分析算法并提取关键信息 | Claude API |
| CodePlannerAgent | 设计代码结构和实现计划 | Claude API |
| CodeGeneratorAgent | 生成完整Python代码 | Claude API |
| CodeValidatorAgent | 运行并验证代码 | Conda + subprocess |

## 技术栈

- **Python**: 3.12+
- **LLM编排**: LangGraph (自实现的简单工作流，未来可升级到LangGraph)
- **大语言模型**: Claude API
- **PDF解析**: PyPDF2 + pdfplumber
- **代码执行**: subprocess + conda环境隔离

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

编辑 `.env` 文件，设置你的 Claude API Key：

```
ANTHROPIC_API_KEY=your_api_key_here
CLAUDE_MODEL=claude-3-5-sonnet-20241022
```

### 3. 使用

```bash
# 基本用法
python -m src.main --pdf path/to/your/paper.pdf

# 指定输出目录
python -m src.main --pdf paper.pdf --output-dir ./my_output

# 指定conda环境
python -m src.main --pdf paper.pdf --conda-env py12pt

# 跳过验证步骤
python -m src.main --pdf paper.pdf --skip-validation

# 启用详细输出
python -m src.main --pdf paper.pdf --verbose
```

## 项目结构

```
MultiAgentPaperCoder/
├── docs/                   # 设计文档
│   ├── design.md           # 详细设计说明
│   └── architecture.md     # 系统架构设计
├── src/                    # 源代码
│   ├── agents/            # Agent实现
│   │   ├── base.py              # Agent基类
│   │   ├── super_agent.py       # 主控智能体
│   │   ├── pdf_reader.py        # PDF读取器
│   │   ├── algorithm_analyzer.py # 算法分析器
│   │   ├── code_planner.py      # 代码规划器
│   │   ├── code_generator.py    # 代码生成器
│   │   └── code_validator.py    # 代码验证器
│   ├── graph/             # 工作流编排
│   │   └── workflow.py          # 主工作流
│   ├── tools/             # 工具集
│   │   ├── llm_client.py        # LLM客户端
│   │   ├── pdf_parser.py        # PDF解析器
│   │   └── code_executor.py    # 代码执行器
│   └── state/             # 状态管理
│       └── __init__.py          # 状态定义
├── prompts/               # 提示词模板
│   ├── analyzer.txt       # 算法分析提示词
│   ├── planner.txt        # 代码规划提示词
│   └── generator.txt      # 代码生成提示词
├── examples/              # 示例代码
│   └── test_simple.py    # 基础测试脚本
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

````python
output/generated_code/
├── main.py              # 主训练脚本
├── model.py             # 模型定义
├── data_loader.py       # 数据加载
├── config.py            # 配置文件
├── utils.py             # 工具函数
└── requirements.txt     # 依赖列表
````

### 2. 执行报告

系统会输出详细的执行报告，包括：

- 论文标题和基本信息
- 算法名称和类型
- 生成的文件列表
- 验证结果（成功/失败）
- 错误日志（如有）
- 修复建议（如有）

## 开发指南

### 运行测试

```bash
# 基础功能测试
python examples/test_simple.py
```

### 添加新的Agent

1. 继承 `BaseAgent` 类
2. 实现 `__call__` 方法
3. 在 `workflow.py` 中注册

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

在 `prompts/` 目录下修改对应的 `.txt` 文件：

- `analyzer.txt`: 控制算法分析的行为
- `planner.txt`: 控制代码规划的策略
- `generator.txt`: 控制代码生成的风格

## 技术决策

### 为什么选择LangGraph而不是DeepAgents？

LangGraph具有以下优势：
- 更成熟的生态系统
- 完善的文档和示例
- 更好的社区支持
- 更灵活的状态管理

注意：当前实现使用了简化的工作流模式，未来可以无缝迁移到LangGraph的StateGraph。

## 注意事项

1. **API Key安全**: 请妥善保管你的 Claude API Key，不要提交到版本控制
2. **成本控制**: 每次处理论文都会调用LLM API，注意监控使用量和成本
3. **Conda环境**: 确保指定的conda环境存在并且Python版本为3.12+
4. **代码安全**: 生成的代码在隔离环境中运行，但建议审查生成的代码

## 未来计划

- [ ] 支持更多LLM模型（GPT-4, LLaMA等）
- [ ] 添加更多代码模板和最佳实践
- [ ] 支持增量更新（只修改需要修改的文件）
- [ ] 添加Web界面
- [ ] 支持论文数据库集成
- [ ] 添加代码质量检查（静态分析、测试覆盖率）

## 文档

- [设计文档](docs/design.md) - 详细的设计说明
- [架构文档](docs/architecture.md) - 系统架构设计

## 许可证

MIT License
