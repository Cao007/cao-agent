---
alwaysApply: true
---

当前项目为 Python 3.13 + FastAPI + LangChain/LangGraph + Vue 3 AI 全栈脚手架。
开始修改前读取根目录 `AGENTS.md`，遵循其中的业务目录、身份隔离、编排和验证约定。
`README.md` 记录实际命令，`docs/DEVELOPMENT.md` 记录三层开发示例。

先确认需求再实现；已有明确实现授权时继续完成，不重复询问。
业务 HTTP / service / workflow 放同一模块，workflow 不依赖 FastAPI。
前端页面按业务组织，API 类型由 OpenAPI 生成。
直接使用官方框架能力，不增加通用基类、DSL 或配置驱动平台。
Docker 管理运行环境；Python 固定 3.13；pnpm 安装使用项目镜像。
未经明确要求，不创建 commit，不推送代码。
