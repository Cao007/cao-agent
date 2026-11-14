# 用这个模板开发业务

## 从模板创建项目

复制仓库后替换 `pyproject.toml` 的项目名、`frontend/package.json` 的包名、
`compose.yaml` 的项目名称、`.env` 的 `APP_NAME` 和前端布局品牌。
不同项目使用不同 Compose 名称，数据库卷也随项目隔离。
多个项目同时运行时设置不同 `WEB_PORT`、`DATABASE_PORT`；
开发环境端口在 `compose.dev.yaml` 中对应修改。
模板复制后各业务项目独立发布，上游修改不会自动同步；记录自己的版本和迁移。

不需要示例时，删除 chat 或 document_analysis 模块，在 `app/main.py` 移除对应
路由与 graph 初始化，在前端删除对应页面、导航和路由，然后重新生成 OpenAPI。
业务数据库迁移历史不要直接删；已有数据时新增迁移。
不需要本地登录时替换 `current_user` 身份依赖，再移除登录页面与模块。

## 需求 → API → 编排 → 页面

示例：新增“邮件草稿”，用户输入收件人称呼、沟通目的和要点，
输出邮件标题与正文。只生成草稿，不发送邮件。验收条件：
输入必填且有长度限制；结果遵循 schema；失败可重试；不混入他人的数据；
不把供应商异常显示给用户。

与 AI 工具确认这些约束后，明确发出实现指令。然后：

1. 新增 `modules/email_draft/schemas.py`：定义 `DraftInput` 和 `DraftResult`。
   新增 `router.py` 的 `POST /api/email-drafts`，使用 `AuthenticatedUser`。
   简单无状态功能直接返回结果；需要保存记录时建立 ORM 表和 Alembic 迁移，
   所有查询按当前用户过滤。
2. 新增 `workflow/graph.py`：调用传入的官方模型
   `model.with_structured_output(DraftResult).ainvoke(...)`。
   该功能只有一次模型调用，无需为了文件名称强行建立 StateGraph。
   多步骤草稿审核时参考 document_analysis 的内部 state、图和 resume。
3. 在 `app/main.py` 注册领域路由。
   导出 OpenAPI、生成前端类型，再新增
   `views/email-draft/index.vue` 的表单和结果组件，在 router 与布局中加入入口。
   请求类型由生成客户端驱动，业务状态留在页面中。
4. 验收必填/超长输入、合法结果、供应商失败、用户隔离，以及页面提交和重试。
   用测试替身验证工程链路，再单独验证真实模型质量。

这个扩展不需要修改公共 AI 层，不需要注册一个万能“应用对象”，也不需要自研工作流引擎。

## 两个已实现示例的契约

| 业务 | 需求 | API | 编排 | 页面 | 关键验收 |
| --- | --- | --- | --- | --- | --- |
| 对话 | 多轮交流，刷新后保留 | `/api/chat/threads`、`/{id}/messages` | MessagesState + respond 节点 | `views/chat/` | 历史恢复、SSE、停止、用户隔离 |
| 文档抽取 | 原文 → 类型约束结果，可审核 | `/api/analyses`、`/{id}/run`、`/{id}/resume` | extract → review / interrupt | `views/document-analysis/` | 候选与正式结果区分、通过/拒绝、重启恢复 |

`router` 负责 HTTP 校验和依赖，`service` 负责归属、公开映射和业务存储，
`workflow` 只负责模型与流程。图状态可以包含原文和中间结果，
但浏览器只接收明确公开的消息、候选结果和正式结果。

## 扩展工具、RAG 和人工审核

`examples/tool_agent.py` 使用 `create_agent` 和服务端 `ToolRuntime`。
将示例内的静态订单替换成业务服务，仍用服务端 user_id 筛选。
工具调用有副作用时做权限与业务校验，不能依赖提示词提供权限。
前端需要展示工具过程时，只映射工具名称、运行状态和可公开结果。

`examples/rag.py` 提供文档切分、嵌入、检索、回答和引用映射。
将文档限定在当前用户可访问的集合，先授权再检索。
来源引用与回答一起返回给页面，不能凭模型生成的来源链接构建真实引用。
文件和大内容通过存储引用传递，不能塞进通用 messages 接口。

人工审核的持久化示例已贯通后端和前端。恢复必须先检查用户、业务模块和 graph interrupt，
并持有同一 thread 的锁。`Command(resume=...)` 接收后端已校验的业务决定，
不要给浏览器任意 checkpoint 或 graph state 的修改权限。

## AI 工具规则

Codex 等支持 AGENTS.md 的工具读取根目录约定。Trae 使用
`.trae/rules/project.md`，配置 `alwaysApply: true`，其中指向 AGENTS.md。
格式依据 [Trae 官方规则文档](https://docs.trae.ai/ide/rules)，已检查文件位置与字段。
在新项目的 Trae 设置 → Rules & Memories 中确认规则列出并始终生效。
本次没有启动新的 Codex/Trae 会话完成自动加载实验；该验证仍需在使用的 IDE 中进行。
规则不能代替需求确认或业务验收。
