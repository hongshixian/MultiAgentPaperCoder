# MultiAgentPaperCoder 架构设计

## 系统架构层次

```
┌─────────────────────────────────────────────────────────┐
│                      用户接口层                           │
│                    (CLI / Python API)                   │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│                    编排层                                 │
│  ┌────────────────────────────────────────────────────┐ │
│  │         PaperCoderSuperAgent                        │ │
│  │     (LangGraph StateGraph + Router)                 │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│                    Agent层                               │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐    │
│  │ PDF  │  │Algo  │  │Code  │  │Code  │  │Code  │    │
│  │Reader│  │Analyzer│Planner│Generator│Validator│  │
│  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘    │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│                    工具层                               │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   │
│  │  LLM    │  │   PDF   │  │  File   │  │  Shell  │   │
│  │ Client  │  │  Parser │  │ Manager │  │Executor │  │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘   │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│                    外部服务层                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                  │
│  │Claude   │  │  File   │  │  Conda  │                  │
│  │  API    │  │  System │  │  Env    │                  │
│  └─────────┘  └─────────┘  └─────────┘                  │
└─────────────────────────────────────────────────────────┘
```

## 组件详细说明

### 1. 用户接口层

**CLI模块** (`src/main.py`)
- 提供命令行接口
- 参数解析和验证
- 进度显示

**API模块** (`src/api.py` - 未来扩展)
- 提供Python API
- 支持异步调用
- Web API支持（可选）

### 2. 编排层

**PaperCoderSuperAgent** (`src/agents/super_agent.py`)
- 基于 LangGraph 的 StateGraph
- 实现路由逻辑
- 管理全局状态流转

### 3. Agent层

所有Agent继承自统一的基类 `BaseAgent`：

```python
class BaseAgent(ABC):
    @abstractmethod
    def __call__(self, state: PaperState) -> PaperState:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass
```

### 4. 工具层

**LLMClient** (`src/tools/llm_client.py`)
- 封装 Claude API 调用
- 支持流式输出
- 错误重试机制
- Token使用统计

**PDFParser** (`src/tools/pdf_parser.py`)
- PDF文件读取
- 文本提取和清洗
- 章节结构解析

**FileManager** (`src/tools/file_manager.py`)
- 文件创建和写入
- 目录管理
- 文件验证

**ShellExecutor** (`src/tools/code_executor.py`)
- subprocess 执行封装
- Conda 环境调用
- 输出捕获和解析

## 数据流图

```
PDF文件
   │
   ├─→ PDFParser ──→ paper_content
   │                           │
   │                           ├─→ AlgorithmAnalyzer
   │                           │          │
   │                           │          ├─→ algorithm_analysis
   │                           │          │        │
   │                           │          │        ├─→ CodePlanner
   │                           │          │        │        │
   │                           │          │        │        ├─→ code_plan
   │                           │          │        │        │        │
   │                           │          │        │        │        ├─→ CodeGenerator
   │                           │          │        │        │        │          │
   │                           │          │        │        │        │          └─→ generated_code
   │                           │          │        │        │        │                        │
   │                           │          │        │        │        │                        └─→ CodeValidator
   │                           │          │        │        │        │                                     │
   │                           │          │        │        │        │                                     └─→ validation_result
```

## 状态机图

```
        ┌──────────┐
        │  START   │
        └────┬─────┘
             │
        ┌────▼─────┐
        │READING   │───┐
        └────┬─────┘   │
             │         │ error
        ┌────▼─────┐   ▼
        │ANALYZING │─────────┐
        └────┬─────┘         │
             │               │ error
        ┌────▼─────┐         ▼
        │ PLANNING │─────────────┐
        └────┬─────┘             │
             │                   │ error
        ┌────▼─────┐             ▼
        │GENERATING│─────────────────┐
        └────┬─────┘                 │
             │                       │ error
        ┌────▼─────┐                 ▼
        │VALIDATING│─────────────────────┐
        └────┬─────┘                     │
             │                           │
        ┌────▼─────┐                     │
        │  DONE    │◀────────────────────┘
        └──────────┘
```

## 错误处理策略

### 错误分类

1. **可恢复错误**
   - 临时网络错误
   - LLM API 限流
   - 文件系统暂时不可用

2. **需要人工干预的错误**
   - PDF文件损坏
   - 论文内容无法解析
   - 依赖包无法安装

3. **致命错误**
   - 配置错误
   - 权限不足
   - 资源不足

### 错误恢复机制

```
Error Occurred
      │
      ├─→ Is Recoverable?
      │       │ Yes
      │       ├─→ Retry Count < Max?
      │       │       │ Yes
      │       │       ├─→ Retry
      │       │       │
      │       │       └─→ Mark as Failed
      │       │
      │       └─→ Mark as Failed
      │
      └─→ Log Error
            │
            └─→ Return Error Report
```

## 配置管理

### 配置文件结构 (`.env`)

```
# LLM Configuration
ANTHROPIC_API_KEY=your_api_key_here
CLAUDE_MODEL=claude-3-5-sonnet-20241022
CLAUDE_MAX_TOKENS=4096

# Environment Configuration
CONDA_ENV_NAME=py12pt
OUTPUT_DIR=./output/generated_code

# Execution Configuration
MAX_RETRIES=3
TIMEOUT_SECONDS=300
ENABLE_CACHE=true
```

### 配置加载优先级

1. 环境变量
2. `.env` 文件
3. 默认配置

## 扩展点设计

### 添加新的Agent

1. 继承 `BaseAgent`
2. 实现 `__call__` 和 `name` 属性
3. 在 `workflow.py` 中注册

### 添加新的工具

1. 在 `src/tools/` 目录创建新工具类
2. 在需要的Agent中导入使用

### 自定义Prompt

1. 在 `prompts/` 目录创建 `.txt` 文件
2. 在对应的Agent中加载使用

## 性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 单篇论文处理时间 | < 10分钟 | 取决于论文复杂度 |
| LLM调用次数 | < 20次 | 优化prompt减少调用 |
| 代码生成成功率 | > 80% | 持续优化prompt |
| 内存占用 | < 2GB | 不包括LLM缓存 |

## 安全架构

```
┌─────────────────────────────────────────────────┐
│           安全边界                              │
│  ┌─────────────────────────────────────────┐  │
│  │    代码执行沙箱 (Conda Env)              │  │
│  │         生成的代码                        │  │
│  └─────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
         │
         ├─→ 限制文件系统访问权限
         ├─→ 限制网络访问
         ├─→ 设置内存/CPU限制
         └─→ 定期超时终止
```

## 部署架构

### 本地部署

```
用户机器
    ├── MultiAgentPaperCoder (本系统)
    ├── Conda环境 (py12pt)
    └── 生成的代码输出目录
```

### 未来可能的云端部署

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Web Server │────▶│  API Server  │────▶│  Worker Node │
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  Result DB   │
                     └──────────────┘
```
