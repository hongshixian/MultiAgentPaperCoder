# MultiAgentPaperCoder

一个面向论文代码复现的多智能体原型系统。当前实现采用 `LangGraph + LangChain Agent` 的混合架构：用确定性工作流控制阶段流转，用子智能体完成论文分析、代码生成、代码验证和错误修复。

## 当前实现

当前主实现位于 `src/hybrid/`，执行流程为：

1. 读取论文 PDF
2. 生成结构化分析报告
3. 基于分析报告生成最小可运行 Python 项目
4. 安装依赖并执行生成代码
5. 若验证失败，进入有限次修复循环

工作流包含 4 个子智能体节点：

- `document-analyst`：读取论文并输出复现分析
- `code-generator`：生成最小可运行代码骨架
- `code-verifier`：安装依赖并执行 `main.py`
- `error-repairer`：根据验证结果修复代码

其中路由逻辑由 `src/hybrid/workflow.py` 中的确定性条件判断负责，不依赖 LLM 自主决策。

## 项目结构

```text
MultiAgentPaperCoder/
├── src/
│   └── hybrid/
│       ├── main.py
│       ├── workflow.py
│       ├── agents.py
│       ├── config.py
│       ├── state.py
│       ├── schemas.py
│       ├── prompts.py
│       ├── callbacks.py
│       ├── logging_utils.py
│       └── tools/
│           ├── pdf_tools.py
│           ├── artifact_tools.py
│           └── exec_tools.py
├── docs/
│   ├── design.md
│   ├── hybrid-architecture.md
│   └── code-architecture.md
├── paper_examples/
├── test_cases/
└── requirements.txt
```

## 代码使用步骤

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 复制环境变量模板：

```bash
cp .env.example .env
```

3. 按需修改 `.env`。默认示例是智谱兼容接口：

```bash
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
MODEL_NAME=glm-4.7
OUTPUT_ROOT=./output
```

如果使用 OpenAI 官方接口，可改为：

```bash
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-5.4
OUTPUT_ROOT=./output
```

配置说明：

- `MODEL_NAME` 支持直接写模型名，也支持带前缀形式；运行时会自动取冒号后的真实模型名
- `OUTPUT_ROOT` 是所有运行产物的根目录
- 每次执行会在 `OUTPUT_ROOT` 下创建一个带时间戳的独立目录

4. 运行 CLI：

```bash
python -m src.hybrid.main --pdf ./paper_examples/1607.01759v3.pdf --output-dir ./output
```

常用可选参数：

- `--max-iterations`：最大修复迭代次数，默认 `5`
- `--log-level`：`info` 或 `debug`，默认 `info`

示例：

```bash
python -m src.hybrid.main \
  --pdf ./paper_examples/1703.03130v1.pdf \
  --output-dir ./output \
  --max-iterations 3 \
  --log-level debug
```

## 输出内容

单次运行会生成类似结构：

```text
output/
├── logs/
│   └── agent_run_YYYYMMDD_HHMMSS.log
└── YYYYMMDD_HHMMSS_<paper_name>/
    ├── artifacts/
    │   └── paper_analysis.md
    └── generated_code/
        ├── main.py
        ├── requirements.txt
        └── ...
```

其中：

- `artifacts/paper_analysis.md` 是论文分析结果
- `generated_code/` 是生成并修复后的代码目录
- `output/logs/` 下保存整次运行日志

## 当前验证能力

当前代码验证阶段的实际行为是：

1. 若存在 `requirements.txt`，执行 `pip install -r requirements.txt`
2. 执行生成项目中的 `main.py`
3. 基于退出码、`stdout` 和 `stderr` 生成结构化验证结果
4. 在需要修复且未达到上限时进入修复循环

当前实现已经提供但未作为主验证链路公开暴露的辅助执行工具包括：

- Python 语法检查
- 入口文件存在性检查

这意味着当前版本更接近“最小可运行闭环”，还不是严格的训练复现验证。

## 测试

运行测试：

```bash
pytest -q
```

当前测试主要覆盖：

- 工作流路由逻辑
- 状态与结构化输出模型
- 文件工具和路径沙盒限制
- 执行工具的基础行为

## 开发文档

- [设计说明](docs/design.md)
- [混合架构设计](docs/hybrid-architecture.md)
- [代码架构说明](docs/code-architecture.md)
