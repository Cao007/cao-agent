# 项目开发约定

本项目是独立 AI 业务应用的模板，技术栈为 Python 3.13、FastAPI、LangChain/LangGraph、
Vue 3 Composition API、TypeScript、Pinia、Element Plus、Vite、PostgreSQL。

1. 先确认业务需求、输入输出和验收条件，再实现代码。用户明确说“开始实现”或明确要求修改时，
   沿用已确认的范围执行，不重复请求批准。
2. 按业务聚合：HTTP 放 `backend/app/modules/<业务>/router.py`，
   对外 schema 放 `schemas.py`，业务规则和存储按需放 `service.py` / `models.py`，
   编排放该模块 `workflow/`，页面放 `frontend/src/views/<业务>/index.vue`。
3. 调用方向为 router → service（按需）→ workflow → 官方模型/工具。
   workflow 不导入 FastAPI Request、Response、HTTPException。
   图内部 state 与 API schema 分开，通过 service 映射公开结果。
4. 直接使用 `init_chat_model`、`create_agent`、`StateGraph`、checkpointer、
   `interrupt`、`Command(resume=...)`。不要引入万能基类、流程 DSL、
   Repository 框架、插件平台或所有供应商的统一 SDK 包装。
5. 公共 `ai/` 只放确实复用的集成点。无复杂编排的功能可直接调用模型。
   文件按实际复杂度拆分，不生成空目录和转发类。
6. 用户身份由后端依赖确定。访问业务记录和 checkpoint 前检查 owner 与 module，
   同一 thread 的修改需使用 `claim_thread`；写 API 校验 CSRF。
   工具的用户上下文由后端注入，不能让模型填写 user_id。
7. 密钥不得放前端。流式输出仅发送公开消息/领域事件，
   不发送内部推理、提示词、原始异常或未经筛选的图状态。
   `interrupt` 前避免不可重复的写操作；节点恢复会重新执行。
8. schema 改动后从根目录执行 `uv run python -m backend.export_openapi`、
   `pnpm --dir frontend generate:api`，同步修改页面。禁止手改生成类型文件。
9. 数据表变更用 Alembic；不在 worker 启动时自动 `create_all` 或执行迁移。
   `checkpoints` / `checkpoint_*` 表由官方 saver 管理，业务表不使用这些名称，
   Alembic autogenerate 已排除它们。
   开发与部署使用 Docker Compose，普通停止不得删除命名数据卷。
   Python 保持 3.13，pnpm 安装使用项目镜像，保留锁文件。
10. 验证 `uv run ruff check backend examples`、`uv run ruff format --check backend examples`、
    `TEST_DATABASE_URL=<独立测试库> uv run pytest -q`、
    `pnpm --dir frontend test`、`pnpm --dir frontend build`；
    跨层改动还需按需求验收页面与 API。不得把演示模式成功说成真实供应商验证。

完整启动步骤见 README.md，新业务示例见 docs/DEVELOPMENT.md。
注释说明约束和取舍，不复述代码。未经用户明确要求，不创建 commit 或推送代码。
