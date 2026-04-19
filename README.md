# MultiAgentPaperCoder

一个基于 `deepagents` 的论文代码复现原型。它的目标是读取论文 PDF，分析论文方法，生成最小可运行代码骨架，并对生成结果做基础验证与修复迭代。

## 当前实现

这个分支提供的是 `deepagents` 版本的实现骨架，核心设计来自 [docs/deepagents-multi-agent-guide.md](/home/lihao/git/MultiAgentPaperCoder/docs/deepagents-multi-agent-guide.md:1)。

系统角色分为：

- 主智能体：任务规划、调度子智能体、汇总最终结果
- `document-analyst`：读取论文并提取结构化复现信息
- `code-generator`：生成最小可运行 Python 项目骨架
- `code-verifier`：检查入口文件和 Python 语法
- `error-repairer`：根据验证错误修复生成代码

## 项目结构

```text
MultiAgentPaperCoder/
├── app/
│   ├── agent.py
│   ├── config.py
│   ├── main.py
│   ├── prompts.py
│   ├── schemas.py
│   ├── subagents.py
│   └── tools/
│       ├── artifact_tools.py
│       ├── exec_tools.py
│       └── pdf_tools.py
├── docs/
│   └── deepagents-multi-agent-guide.md
├── paper_examples/
├── src/                    # 保留原 LangGraph 实现
└── test_cases/
```

## 安装

```bash
pip install -r requirements.txt
```

## 配置

复制环境变量模板：

```bash
cp .env.example .env
```

最少需要配置：

```bash
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-5.4
OUTPUT_ROOT=./output
```

如果你使用智谱这类 OpenAI 兼容接口，也仍然用同一套变量：

```bash
OPENAI_API_KEY=your_zhipu_api_key_here
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
MODEL_NAME=glm-5
```

## 使用方式

运行 `deepagents` 版入口：

```bash
python -m app.main --pdf ./paper_examples/1607.01759v3.pdf --output-dir ./output
```

执行时，主智能体会尝试：

1. 读取论文 PDF
2. 调用文档分析子智能体
3. 生成最小代码项目
4. 进行入口文件和语法验证
5. 在失败时尝试修复并重新验证

## 当前验证能力

当前版本的验证是“最小闭环”：

- 检查 `main.py` 是否存在
- 对生成项目做 Python 语法检查

这还不是完整训练验证。后续建议扩展：

- requirements 安装检查
- smoke test
- 真正的训练脚本执行
- 结果指标比对

## 开发文档

- DeepAgents 开发指南：[docs/deepagents-multi-agent-guide.md](/home/lihao/git/MultiAgentPaperCoder/docs/deepagents-multi-agent-guide.md:1)

## 测试

```bash
pytest -q
```

## 备注

- `src/` 中的旧 LangGraph 实现暂时保留，方便对比迁移
- `app/` 是当前分支上的 DeepAgents 主实现
