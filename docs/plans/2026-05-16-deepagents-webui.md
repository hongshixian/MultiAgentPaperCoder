# DeepAgentsWebUI 实施计划

> **分支:** deepAgentsWebui
> **目标:** 为 MultiAgentPaperCoder 新增 Web 任务管理与可视化层
> **原则:** 零改动现有代码，纯 HTML/JS 前端，FastAPI 后端

---

## 任务列表

### Task 1: 创建 webui 模块骨架 + 依赖

**文件:**
- Create: `src/webui/__init__.py`
- Create: `src/webui/app.py` (FastAPI 骨架)
- Modify: `requirements.txt` (追加 fastapi/uvicorn/aiosqlite/python-multipart)

**内容:**
- FastAPI 应用骨架，返回 `{"status": "ok"}`
- 验证: `uvicorn src.webui.app:app --port 8000` 可启动

### Task 2: 任务数据模型 + SQLite 初始化

**文件:**
- Create: `src/webui/models.py`

**内容:**
- `Task` dataclass + SQLite 建表
- `init_db()` / `create_task()` / `get_task()` / `list_tasks()` / `update_task()`

### Task 3: REST API — 任务 CRUD

**文件:**
- Create: `src/webui/routes/__init__.py`
- Create: `src/webui/routes/tasks.py`

**API 端点:**
- `GET  /api/tasks` — 任务列表
- `GET  /api/tasks/{id}` — 单个任务
- `POST /api/tasks` — 创建任务（上传 PDF + 参数）
- `GET  /api/tasks/{id}/output` — 产物文件列表

### Task 4: 后台任务执行器

**文件:**
- Create: `src/webui/runner.py`

**内容:**
- `async run_paper_task(task_id, pdf_path, max_iterations)` 
- 包装现有 `create_workflow()` + `workflow.invoke()`
- 每进入节点时更新 SQLite + 推送 WebSocket

### Task 5: WebSocket 实时推送

**文件:**
- Create: `src/webui/routes/websocket.py`

**内容:**
- `ws://localhost:8000/ws/{task_id}` 
- 连接管理 (dict[task_id, list[WebSocket]])
- `push_event(task_id, event)` 广播函数

### Task 6: 前端 — HTML 骨架 + 样式

**文件:**
- Create: `src/webui/templates/index.html`

**内容:**
- 暗色主题 CSS
- 页面结构：顶栏 + 任务列表区 + 新建按钮

### Task 7: 前端 — 任务列表渲染

**修改:** `src/webui/templates/index.html`

**内容:**
- JS fetch `GET /api/tasks` 渲染卡片列表
- 状态标签样式 (pending/running/passed/failed)
- 轮询刷新

### Task 8: 前端 — 新建任务弹窗

**修改:** `src/webui/templates/index.html`

**内容:**
- 弹窗表单：文件上传 + 参数配置
- `POST /api/tasks` multipart/form-data

### Task 9: 前端 — 任务详情 + WebSocket 实时更新

**修改:** `src/webui/templates/index.html`

**内容:**
- 点击卡片展开详情面板
- 建立 WebSocket 连接
- 实时更新节点状态图 + 进度条
- 任务完成后展示摘要

### Task 10: 端到端测试 + 验证

**内容:**
- 启动服务 → 上传 PDF → 观察实时状态 → 查看结果
- 修复遗漏问题