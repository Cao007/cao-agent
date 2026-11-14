# Cao AI 框架扩展验证：MewHelp 客服

验证日期：2026-11-14。分支：`feat/ai-customer-service`。
结论：现有框架可以扩展为含 RAG、业务工具、持久化中断恢复及运营反馈链路的客服应用。
本次验证覆盖 Docker 演示环境和离线模型协议替身，尚未证明真实供应商的语义质量。

## 扩展位置

| 层 | 本次实现 | 框架复用 |
|---|---|---|
| HTTP | `backend/app/modules/customer_service/router.py` | 登录依赖、CSRF、owner/module 校验、thread advisory lock |
| 业务 | `models.py`、`service.py`、`retrieval.py` | SQLAlchemy 会话、Alembic、公开 schema 映射 |
| 编排 | `workflow/graph.py` | 官方 StateGraph、create_agent、ToolRuntime、interrupt、Command、PostgresSaver |
| 客户页面 | `frontend/src/views/customer-service/index.vue` | Vue Composition API、类型化客户端、POST SSE 与取消 |
| 运营页面 | `customer-service/operations/` | Element Plus、OpenAPI 生成类型 |

新增六张客服业务表。运营身份由独立 membership 表控制；不引入通用权限平台、
Repository、流程 DSL 或供应商 SDK 包装。workflow 不依赖 FastAPI。
公共 AI 层无需调整，客服进度与回答由模块 service 映射到已有 SSE 输出。

## 验证结果

| 验证 | 结果与证据 |
|---|---|
| 后端检查 | Ruff lint / format 通过 |
| 框架与客服测试 | 独立 PostgreSQL 测试库：17 项通过（原框架 11，客服 6） |
| 前端 | SSE 测试通过，vue-tsc 和 Vite build 通过 |
| 数据迁移 | 主库与独立测试库升级到 `84688d40ac0b`，官方 checkpoint 表仍由 saver 管理 |
| Docker | Python 3.13 生产镜像构建，migrate 完成，backend 健康，Nginx 提供客服页面 |
| 浏览器 | 登录、知识引用展开、订单点选恢复、退款、未知问题人工工单、审核入库、RAG 评估 |
| HTTP | 带真实 cookie/CSRF 的请求验证引用、物流、代词关联、审核后检索、兜底、后台权限和 owner 隔离 |
| 模型调用边界 | 离线 BaseChatModel 替身驱动官方 Agent 实际调用两项工具，验证结构化引用、门控和实测 usage 汇总 |
| 恢复 | 应用重启后恢复订单中断；失败节点重试不重复保存轮次；重复恢复/审核拒绝 |

自动 HTTP 证据见 [CUSTOMER_SERVICE_VERIFICATION.json](CUSTOMER_SERVICE_VERIFICATION.json)。
浏览器实际窄屏页面截图见 [customer-service.png](customer-service.png)。
主库最终评估包含 10 道本项目样例：5 道有预期知识的检索题、1 道未知检索题、
4 道业务/问候分类题。浏览器审核补充知识后，同步更新原未知题，并补充新的未知负例。
这套样例很小且偏直接匹配；四策略均得到 Recall@3=1、MRR@3=1，
覆盖度为 5/6，分类准确率为 1。结果说明指标确实由数据计算，
不能用于选择真实业务检索策略或宣称生产质量。

## 本次发现

1. 中文订单编号不能使用英文单词边界 `\b`；“订单1001物流”在最初实现中
   被误判为缺少编号，已改为数字边界，并由端到端客服测试覆盖。
2. checkpoint 在停止或异常后可能仍有待执行节点。新增受 owner 和锁保护的重试入口，
   使用官方图恢复未完成节点；订单 interrupt 必须继续通过已校验的选择恢复。
3. 完整答案需要引用校验。客户会话只存公开 Human/AI 消息与业务结果，
   Agent 工具内部消息不直接暴露给前端。
4. 后台同步知识和索引可用一个数据库事务完成；小规模无需新增任务队列。
5. 运营评估、分类器、主题和费用必须基于真实记录；演示没有模型用量，费用显示未知。

## 仍需验证

真实 embedding、模型工具选择与回答、聊天重排质量、独立评估集阈值、真实订单系统接入。
真实模型能力需要供应商密钥和相应模型权限，当前未联网验证。
检索扫描上限为 500 篇知识；索引同步执行；流式回答以进度事件和最终完整回答呈现。
前端构建保留了框架既有 Element Plus 主包体积提示，未新增前端依赖。
这些限制及运行命令见 [CUSTOMER_SERVICE.md](CUSTOMER_SERVICE.md)。
