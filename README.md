# MewHelp：基于 Cao AI 框架的智能客服

FastAPI + Python 3.13 + Vue 3 + LangChain/LangGraph。当前分支为独立客服应用：
知识问答与引用、订单/物流工具、退款研判、订单中断点选、人工工单和知识反馈链路。
运营工作台包含知识库、四策略 RAG 评估、待审队列、成本、主题和分类器验收。

[客服运行与验收说明](docs/CUSTOMER_SERVICE.md) ·
[框架扩展验证报告](docs/FRAMEWORK_CUSTOMER_SERVICE_ASSESSMENT.md) ·
[来源与需求](docs/CUSTOMER_SERVICE_REQUIREMENTS.md)。

默认服务只有 PostgreSQL、FastAPI 和前端；不需要 Redis、任务队列或云追踪。
复用框架的登录、会话持久化、人工审核与恢复、OpenAPI 类型生成。
原框架示例仍可通过 `/chat`、`/analysis` 访问，默认入口为 `/support`。

## Docker 启动

```bash
cp .env.example .env
docker compose up -d --build
```

访问 http://localhost:8080 ，首次使用点击“创建账户”。没有预设管理员或默认登录密码。
API 文档：http://localhost:8080/api/docs 。
默认 `MODEL_MODE=demo`，输出明确标注为演示，不调用付费模型。
迁移容器先完成 Alembic 和官方 checkpointer 初始化，后端才启动。

```bash
docker compose logs -f backend
docker compose down
```

普通停止保留命名数据卷。`down -v` 会删除数据库，不能用于日常停止。
默认仅向本机开放 Web 与数据库端口。

开发环境支持 Python reload 和 Vite HMR：

```bash
docker compose -f compose.yaml -f compose.dev.yaml up -d --build
```

访问 http://localhost:5173 ，后端：http://localhost:8000/api/docs 。
切换回生产模式时，显式重新构建并启动：

```bash
docker compose up -d --build
```

后端和前端分别挂载 `backend/` 与 `frontend/src/`。修改依赖后重新构建。
Vite 容器通过服务名 `backend:8000` 代理 API。

## 配置真实模型

在 `.env` 中设置：

```dotenv
MODEL_MODE=openai
OPENAI_API_KEY=你的密钥
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4.1-mini
```

然后 `docker compose up -d --force-recreate backend`。
模型由官方 `init_chat_model` 创建；替换供应商时安装官方 provider 包并修改
`backend/app/ai/model.py`。结构化抽取需要模型支持结构化输出。
密钥只能留在服务端，不能放入 `VITE_` 环境变量。

生产部署需设置数据库强密码、HTTPS、`COOKIE_SECURE=true`、准确的
`ALLOWED_ORIGINS`，按业务决定是否关闭 `ALLOW_REGISTRATION`。
登录是可替换的独立模块。公网身份入口需结合网关限速或企业身份服务，
此模板没有预置复杂账户管理。

pnpm 默认使用项目 `.npmrc` 的 npmmirror。Docker 构建可用 `NPM_REGISTRY` 覆盖。
如 Docker Hub 网络不可用，可覆盖 `PYTHON_IMAGE`、`NODE_IMAGE`、
`NGINX_IMAGE`、`UV_IMAGE`，不必修改 Dockerfile，例如：

```bash
PYTHON_IMAGE=mirror.gcr.io/library/python:3.13-slim \
NODE_IMAGE=mirror.gcr.io/library/node:24-alpine \
NGINX_IMAGE=mirror.gcr.io/library/nginx:1.28-alpine \
docker compose up -d --build
```

基础镜像固定版本系列，应用依赖使用 `uv.lock` 和 `pnpm-lock.yaml` 锁定。
派生项目可进一步固定镜像 digest。

## 改哪里

```text
backend/
  app/
    main.py                     路由组装和生命周期
    core/                       配置、身份依赖、日志
    db/                         SQLAlchemy 引擎与会话
    ai/                         官方模型、checkpointer、流式 HTTP 边界
    modules/
      auth/                     登录、当前用户与会话
      threads/                  会话归属与数据库并发锁
      chat/
        router.py               对话领域 API
        schemas.py              对外接口类型
        service.py              输入和公开消息映射
        workflow/graph.py       官方 MessagesState / StateGraph
      document_analysis/
        router.py               抽取、审核与结果 API
        schemas.py              请求与公开结果
        models.py               正式业务结果
        service.py              状态到领域结果的映射
        workflow/               内部状态与 extract → review 图
  migrations/                   Alembic 业务迁移
  tests/                        PostgreSQL 集成验收
frontend/src/
  api/                          OpenAPI 类型、客户端、POST SSE
  components/ai/                消息与抽取结果组件
  layouts/                      工作空间布局
  router/                       路由与登录守卫
  stores/                       仅共享身份状态
  views/                        各业务页面
examples/                       工具 Agent、RAG、interrupt/resume
```

一个新功能通常只新增 `modules/<业务>/` 和对应 `views/<业务>/`，在入口注册路由。
只有出现实际复用需求时才修改公共 `ai/`。简单模型调用无需建立 graph 或 service。
完整三层开发流程与示例验收见 [开发指南](docs/DEVELOPMENT.md)。

## 本机检查

项目运行以 Docker 为主；本机命令用于快速检查，需要 Python 3.13、uv、Node 24、pnpm 10。

```bash
docker compose up -d db
uv sync --frozen
uv run python -m backend.migrate
uv run uvicorn backend.app.main:app --reload
```

另一个终端：

```bash
pnpm --dir frontend install --frozen-lockfile --registry=https://registry.npmmirror.com
pnpm --dir frontend dev
```

后端 schema 改动后，从根目录生成客户端并重新检查前端：

```bash
uv run python -m backend.export_openapi
pnpm --dir frontend generate:api
pnpm --dir frontend build
pnpm --dir frontend test
uv run ruff check backend examples
uv run ruff format --check backend examples
```

后端集成测试使用独立 PostgreSQL 数据库，不能指向业务生产库。
首次创建和迁移：

```bash
docker compose exec db psql -U cao -d postgres -c 'CREATE DATABASE cao_test'
DATABASE_URL=postgresql://cao:cao@localhost:5432/cao_test uv run python -m backend.migrate
TEST_DATABASE_URL=postgresql://cao:cao@localhost:5432/cao_test uv run pytest -q
```

测试创建随机用户和业务记录，不调用真实供应商。未设置测试库时集成测试会跳过。
CI 配置见 `.github/workflows/ci.yaml`。

## 可复制示例

```bash
uv run python -m examples.human_review
uv run python -m examples.tool_agent
uv sync --extra rag
uv run --extra rag python -m examples.rag
```

人工审核 CLI 无密钥可运行；持久化与前端审核的完整版本在文档抽取模块。
工具 Agent 使用官方 `create_agent` 和 `ToolRuntime`，当前用户由服务端上下文决定。
RAG 使用官方 splitter、embedding 和内存向量存储，返回来源引用。
后两者需要真实模型权限，RAG 还需要 embedding 权限。
内存 RAG 示例只适用于小型演示，业务知识库需增加文件存储、访问隔离和持久化索引。

## 运行边界

身份会话使用 HttpOnly、SameSite cookie；数据库只存令牌摘要，写操作校验 CSRF。
每个 thread 关联用户和业务模块，不能通过猜测 ID 访问或恢复他人的记录。
同一个 thread 使用 PostgreSQL 事务级 advisory lock，并发请求返回 409；
运行期间占用一条数据库连接，扩展大并发或长任务时需重新评估执行服务与连接池。

checkpointer 保存图状态，业务表只保存归属、状态与正式抽取结果。
刷新页面可读取已保存状态，审核暂停可在服务重启后继续。
候选结果审核通过才写入正式结果；拒绝结束流程并保留审核记录。
请求取消会停止上游调用，未完成节点的部分 token 不作为完整回答保存。
进程被强制结束时，业务 `running` 状态可能暂留，数据库锁会自动释放；
对话可继续，抽取可重新调用 `/run` 恢复未完成节点。

默认是请求级执行，断线不保证后台继续。没有运行重连、事件重放、分布式任务队列，
也不将 checkpointer 当作后台任务服务。SSE 只发送公开文本、领域进度和结果，
不透传内部提示词、完整 graph state 或原始异常。
官方 Vue SDK 的接入取舍见 [流式验证记录](docs/STREAMING.md)。

可选 LangSmith 追踪通过运行环境设置 `LANGSMITH_TRACING`、
`LANGSMITH_API_KEY`、`LANGSMITH_PROJECT`。Pydantic 读取 `.env` 不会把这些额外字段
自动导入进程；Compose 的 `env_file` 会将它们传给容器。

工具规则入口为 `AGENTS.md` 和 `.trae/rules/project.md`，规则并不能保证 AI 工具自动生成正确业务。
使用与验证记录见 [验收记录](docs/VERIFICATION.md)。
