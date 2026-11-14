# 首版验收记录

验证环境：macOS arm64，Python 3.13.17，Node 24.13.0，pnpm 10.29.3，
Docker Desktop / Compose，实际 PostgreSQL 17 容器。

容器 Python：3.13.18；pnpm 构建安装和运行时配置均为 npmmirror。

| 检查 | 结果 |
| --- | --- |
| Ruff 规则与格式 | 通过，36 个 Python 文件 |
| PostgreSQL 集成与工具检查 | 11 项通过 |
| 登录、HttpOnly 会话、CSRF、来源校验 | 通过 |
| 跨用户对话/抽取/恢复隔离 | 通过 |
| 新应用实例读取并继续对话 | 通过 |
| 抽取 schema、审核暂停、重启后通过/拒绝 | 通过 |
| 同 thread 数据库锁及释放 | 通过 |
| 真实 uvicorn HTTP 断连取消模型与锁释放 | 通过 |
| 已完成 checkpoint 补写正式业务结果 | 通过，重复调用幂等 |
| 官方 create_agent / ToolRuntime 上下文隔离 | 通过，使用测试模型 |
| 前端逐字节 SSE 解析 | 1 项通过，覆盖中文、CRLF、断连、失败与暂停 |
| OpenAPI 类型生成、vue-tsc、Vite 生产构建 | 通过 |
| Docker 生产镜像与迁移启动 | 构建通过，服务健康 |
| Alembic autogenerate 边界 | 官方 checkpoint 表排除，业务模型一致性检查通过 |
| Docker 开发容器 | 启动通过，代理 API 返回正常 |
| Python reload | WatchFiles 检测源码变化并完成重新启动 |
| Vue HMR | 容器日志及浏览器均确认页面即时更新 |
| 浏览器业务流程 | 注册、对话、抽取、审核通过与正式结果展示通过 |
| 浏览器响应式检查 | 598px 与 1130px 宽度下表单、导航和结果可操作 |
| 人工审核 CLI | 无密钥 interrupt/resume 检查通过 |

Docker Hub 本次出现匿名 token 请求连接重置，使用 `mirror.gcr.io` 的
Python、Node、NGINX 镜像完成实际构建；uv 使用 GHCR 镜像。
没有修改开发者全局 npm 或 Docker registry 配置。
容器构建中的 pnpm 安装使用 `--frozen-lockfile --registry=https://registry.npmmirror.com`。

本机 pnpm 完成依赖与锁文件写入后，TRAE sandbox 对用户目录临时文件清理报告限制；
后续本机构建通过，Docker 中完整镜像安装与构建也通过。
本机 uv 的 Python 版本别名链接异常，使用完整 3.13.17 可执行文件和 venv copies 修正，
实际本机测试与容器测试均运行在 Python 3.13 系列。

未验证的范围：

- 真实模型与 embedding 供应商的输出质量、token 延迟和工具选择；本次未使用模型密钥。
  模型调用测试使用替身，工具测试使用官方 Agent 搭配测试模型。
- RAG 仅检查可选依赖、分词器与示例导入；真实检索生成需要 embedding 和模型权限。
- Vue 官方 SDK 的运行时兼容；只做协议对照，首版原生 SSE 已单独验证。
- 新 Codex/Trae 会话自动加载规则及独立新增业务的 AI 开发实验。
  Trae 文件位置和 `alwaysApply` 依据官方规则文档配置。
- GitHub Actions 远端运行；已交付 CI 配置，未提交或推送仓库。

Element Plus 首版全量注册使主 JS 包约 1.05 MB，Vite 有体积提示但构建成功。
需要控制首次加载体积的派生项目可改为组件按需导入。
请求级执行不支持断线续跑、事件重放或可靠后台任务，详见 README 与 STREAMING.md。
