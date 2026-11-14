# 流式通信接入判断

日期：2026-11-14。Python 锁定 LangGraph 1.2.22，LangChain 1.5.0。
当前选择原生 fetch POST SSE，前端解析仅在 `api/stream.ts`，
后端映射仅在 `ai/streaming.py` 和各业务 service。

## 官方 SDK 的协议边界

核对了官方 [Vue useStream](https://reference.langchain.com/javascript/langchain-vue/use-stream)
和 [Transports](https://reference.langchain.com/javascript/langchain-vue/transports) 文档。
Vue SDK 支持自有后端，不要求必须部署完整 Agent Server。
但 `HttpAgentServerAdapter` 需要后端实现 Agent Streaming Protocol：

- `POST /threads/:id/commands` 接收 run.start、resume、取消等命令并返回协议响应。
- `POST /threads/:id/stream` 处理 channels、namespaces、depth、since 订阅。
- SSE data 中是完整协议事件，需要序号、过滤与重放语义。

这比本模板“一个领域 POST 请求执行并输出”的契约更大。
仅换 fetch URL 或包一层 token JSON 不能直接兼容该 SDK。
自定义 `AgentServerAdapter` 也需实现 command 与订阅契约。
这里完成的是官方协议对照，未安装 Vue SDK 做运行时兼容测试，
因此不宣称官方 SDK 已与此 FastAPI 后端集成成功。

首版采用方案中允许的轻量回退：保持领域 API，使用 fetch 读取 SSE。
以后确实需要重放、运行重连、多订阅和时间旅行时，再实现官方协议或采用 Agent Server，
届时优先使用官方 Vue SDK，避免维护相同运行能力。

## 已验证的最小传输

SSE 事件仅包含：

| 事件 | 公开含义 |
| --- | --- |
| start | 本次 run_id |
| token | 可展示的文本增量 |
| progress | 领域进度文字 |
| paused | 明确允许用户查看的候选抽取结果 |
| result | 正式结果，拒绝时为 null |
| done | 正常终止 |
| error | 经脱敏的失败说明 |

前端测试将 SSE 逐字节切分，覆盖中文 UTF-8、JSON 换行、CRLF、
正常终止、失败、提前断连和审核暂停。缺少 done/paused 时不能当作成功。
HTTP 错误发生在流开始前，返回状态码；流开始后失败使用 error 事件。

后端使用官方 graph 的 `stream_mode="messages"` 读取文本、
`stream_mode="updates"` 读取允许展示的节点进度。
完整状态通过 `aget_state` 在服务端映射，不能原样发给浏览器。
模型未产生可展示文本时图结果仍需显式校验。
演示输出是完整 AIMessage，按公开文本事件发出，不能用于判断真实模型 token 延迟。

在真实 uvicorn HTTP socket 测试中发现 ASGI 2.4 默认 StreamingResponse
仅在 send 时感知断连。模型等待期间没有 send，会导致 AbortController 未及时取消模型。
`DisconnectAwareResponse` 显式监听 http.disconnect 并取消流任务，
用独立 asyncio 任务发起流与监听，只 cancel 一次并等待 graph 退出。
AnyIO 反复取消会打断 graph 自身的子任务清理，真实 HTTP 测试已覆盖此差异。
取消向 graph/model 传播；清理在 shield 中保存取消状态并释放数据库锁。
这是请求级取消，不能据此承诺可靠后台任务终止或跨设备运行重连。
