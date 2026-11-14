# 轻量级 AI 应用脚手架：调研与建议方案

状态：用户已于调研后明确指示“开始实现代码”；当前已按默认推荐方案实施，验收见 docs/VERIFICATION.md。
调研日期：2026-11-14。

## 1. 项目定位

目标是让团队基于此模板快速创建独立的 AI 全栈业务项目，复用项目结构、公共工程能力及典型 AI 应用实践。主要开发方式由用户明确为：先与 Trae、Codex 等 AI 编程工具确认需求，再直接修改 FastAPI 后端、编排层和 Vue 前端。

对应传统开发中的关系：

- FastAPI、Vue、LangChain、LangGraph 提供基础框架能力。
- 本项目提供可复制的工程结构、集成配置、公共模块、页面组件、测试和部署模板。
- 业务项目直接编写领域接口、页面、模型调用及工作流。

“通用”指业务扩展路径开放：可以开发对话、表单、结构化处理、RAG、工具 Agent、人工审批和多模态应用。它不意味着一个固定聊天入口能自动覆盖所有应用，也不意味着首版预装所有 AI 功能。

默认使用方式建议为“从模板创建一个业务项目”。一个业务项目可以包含多个功能模块；第一版不建设管理多个独立应用的中央平台。

### 1.1 用户明确的开发流程

1. 与 Trae/Codex 确认需求：明确用户交互、输入输出、业务规则、模型/工具需求和验收条件，并确认实现方案。
2. 修改 FastAPI 后端：实现业务 schema、路由、数据存储和权限规则，复用已有配置、身份与日志等公共能力。
3. 修改编排层：按业务需要编写模型调用、LangChain Agent 或 LangGraph 节点与流程，复用官方能力及项目集成点。
4. 修改 Vue 前端：实现业务页面、表单和结果展示，复用 API 客户端、布局及适用的 AI 组件。
5. 按已确认的验收条件检查端到端行为，完成该 AI 全栈应用。

第 2～4 步按具体功能协同迭代，不要求机械地逐层完成。编排层可以与业务模块同目录组织；它是职责边界，不是独立部署服务。无需复杂编排的功能可以直接使用模型。

脚手架应让 AI 编程工具容易判断“改哪里、调用什么、如何验证”。因此，明确且稳定的目录、接口契约、修改规则和完整示例，比增加通用抽象更重要。

### 1.2 AI 编程工具的项目上下文

首版建议交付一份工具通用的开发指南，以 `AGENTS.md` 供 Codex 等支持该约定的工具读取，并为 Trae 配置对应的项目规则入口。不同工具的规则加载方式应分别验证，不假设它们都自动读取同一个文件。

规则只记录实际有效的约定：

- 三层职责、业务功能的位置及公共模块的使用方式。
- 需求/方案确认后才能进入实现，不将讨论或澄清当作开发授权。
- 优先直接使用 FastAPI、LangChain、LangGraph 和 Vue 的原生能力。
- 只有已有重复需求时才提取公共辅助代码，避免新增万能基类和配置驱动平台。
- 后端 schema 变化时更新前端客户端与页面，按验收条件验证跨层行为。
- 开发、测试与构建命令；运行时依赖及部署限制。

完整示例应贯通“需求说明 → 后端接口 → 编排逻辑 → 前端页面 → 验收”，供团队和 AI 编程工具沿用。规则文件辅助开发，不能替代明确的业务需求或保证 AI 工具自动生成正确实现。

## 2. 主流方案比较

以下是基于官方文档的能力与定位比较，不是性能实测或市场占有率排名。

| 方案 | 官方能力与定位 | 对本项目的启示 |
| --- | --- | --- |
| FastAPI Full Stack Template | 预置数据库、认证、OpenAPI 客户端、测试及部署；前端为 React | 最接近工程脚手架思路，借鉴公共工程实践，采用用户要求的 Vue 前端 |
| LangChain + LangGraph 开源库 | 模型集成、Agent、工具、结构化输出、状态图、流式事件、checkpointer/store | 直接使用官方 API，避免再写自己的模型接口、Agent 基类、工作流引擎和记忆框架 |
| LangGraph Agent Server | 完整的 threads/runs、后台执行、持久化等运行服务；官方独立部署方案涉及 PostgreSQL、Redis 和许可配置 | 长期后台任务、运行重连成为核心需求时重新评估；不将该完整运行服务设为轻量首版前提 |
| Dify | 可视化 AI 应用平台；官方 Compose 包含 API、worker、web、插件服务及数据库、Redis、向量库等组件 | 可参考产品交互；其平台范围和默认部署组件不适合本项目的轻量目标 |
| Langflow | 可视化组件与流程编辑、Agent、MCP 和 API 服务 | 可作为流程原型工具；第一版以代码维护业务流程，避免自建组件体系和画布编辑器 |

FastAPI 官方模板与 LangGraph 官方应用结构是两类互补参考：前者解决全栈工程启动，后者解决图应用的组织。没有必要完整 fork 一个大型 AI 平台再删减。

需要区分 LangGraph 开源库、Agent Server 与 LangSmith 平台的部署及许可条件，不能将它们视为同一个组件。本文对 Agent Server 的部署判断依据独立部署文档，不是套用整个 LangSmith 平台的资源要求。

## 3. 建议技术栈

| 部分 | 建议 | 取舍 |
| --- | --- | --- |
| 后端 | Python 3.13、FastAPI、Pydantic Settings、uv | Python 版本由用户明确；容器、开发与 CI 保持一致 |
| AI | LangChain、LangGraph 当前稳定且经过验证的版本 | 普通调用可以直接用模型；需要编排时再用图 |
| 模型接入 | `init_chat_model` / 官方 provider 包 | 只统一团队的默认参数、配置与生命周期；保留官方模型对象 |
| 前端 | Vue 3、TypeScript、Vite、Vue Router、Pinia、pnpm | pnpm 按用户要求使用镜像；业务状态优先留在页面 |
| UI | 建议 Element Plus 与少量项目样式 | 复用表单、表格、弹窗等通用组件，首版不自建 UI 组件库 |
| 业务存储 | PostgreSQL、SQLAlchemy 2、Alembic | 统一一种关系数据库与迁移方式，避免同时维护多数据库适配 |
| 图状态 | 官方 PostgreSQL checkpointer | 复用同一 PostgreSQL 服务，不重复实现图状态存储 |
| 前端 API | OpenAPI 生成 TypeScript 客户端 | 业务请求类型由后端 schema 驱动，流式接口另外处理 |
| 项目运行管理 | Docker Compose、静态前端服务、FastAPI、PostgreSQL | Docker 管理由用户明确；数据库是否默认包含仍待确认 |
| 质量 | Ruff、pytest、vue-tsc、必要的前端集成检查 | 聚焦身份隔离、状态恢复、接口与关键 AI 输出 |
| 追踪 | 结构化运行日志；可选 LangSmith | 默认运行不依赖云追踪服务 |

具体版本与依赖会在实施前的小型接入验证中锁定，避免把调研文档中的最新接口直接当作已经验证的集成。

### 3.1 已确认的环境要求

- 使用 Docker Compose 管理前后端及选用的依赖服务，统一启动、停止、日志和构建入口。
- Python 固定为 3.13：后端容器以 `python:3.13-slim` 系列镜像为基础，项目 Python 版本约定、uv 环境与 CI 使用同一版本系列。依赖锁定及验证以 Python 3.13 为准。
- pnpm 安装依赖使用镜像。暂定 `https://registry.npmmirror.com`，这属于可调整的镜像选择；镜像使用要求本身已由用户确认。
- 镜像配置放在前端项目 `.npmrc`，Docker 构建也使用该配置；提供构建参数或环境配置覆盖镜像地址，不修改开发者全局 npm 配置。
- 保留 `uv.lock` 和 `pnpm-lock.yaml`，容器构建及 CI 使用锁定依赖的安装命令。镜像选择不替代依赖版本锁定。
- 开发容器支持源码挂载、FastAPI reload 与 Vite HMR；容器内监听 `0.0.0.0`，通过 Compose 控制宿主机端口暴露。生产构建使用多阶段镜像，前端产物由静态服务器提供。
- 数据库等持久化数据使用命名卷，日常停止不删除数据卷。容器内前端代理通过 Compose 服务名访问后端，避免使用指向前端容器自身的 `127.0.0.1`。

这些约定会在方案确认后落实到 Dockerfile、Compose、Python 版本文件及项目级 pnpm 配置；本轮仅更新文档。

## 4. 核心边界：只封装项目反复使用的集成点

### 默认提供的工程能力

- 环境配置、服务生命周期、数据库会话与迁移。
- 最小登录与当前用户模块、业务资源归属检查、前端路由守卫。
- 统一异常呈现、请求与运行 ID、基础结构化日志。
- 基础布局、API 客户端、异步加载/失败状态与常用 AI 展示组件。
- 一次性初始化说明、开发命令、容器部署、CI 检查模板。

登录建议作为可删除的独立模块，不建设菜单权限平台、组织架构、复杂 RBAC、租户管理或登录渠道管理。已有企业身份系统的项目可替换身份依赖。认证形式与浏览器凭据存储策略应在接口设计时明确，不将浏览器存储中的长期令牌作为默认方案。

### 默认提供的 AI 集成能力

- 服务端模型配置入口，复用官方 provider 和模型对象。
- 异步调用与流式响应的少量共享代码。
- 图实例生命周期、官方 checkpointer 配置。
- thread 与当前用户/业务模块的关联及访问校验。
- 运行状态、公开结果、取消及人工中断的前后端接入示例。
- 文本、结构化 JSON、工具结果和引用等展示组件。

checkpointer 保存图执行状态；业务表保存用户、业务实体和 thread 归属。二者职责不同，不再复制一份整套图状态作为“自研记忆系统”。

### 直接使用官方能力

| 能力 | 使用方式 |
| --- | --- |
| 模型与多供应商 | `init_chat_model` 与官方 provider 包 |
| 工具 Agent | `create_agent` |
| 工具定义 | 普通 Python 函数或 `@tool` |
| 自定义流程 | `StateGraph`、节点、条件边及子图 |
| 结构化输出 | Pydantic schema、模型结构化输出或 Agent `response_format` |
| 上下文/记忆 | 官方消息、checkpointer 与 store |
| 人工介入 | 官方 interrupt 与 resume 机制 |
| 检索 | 官方 loader、splitter、embedding 和 retriever，按示例安装依赖 |

业务可以直接访问官方对象，公共辅助函数不能屏蔽 `bind_tools`、结构化输出、运行配置、middleware 等能力。不要要求普通的一次性模型调用也必须套一个 LangGraph。

### 首版排除的范围

可视化编排、自研 DSL、插件市场、热加载插件、通用 Repository/Service 基类、全供应商 SDK 包装、模型计费平台、复杂权限系统、知识库管理平台、分布式任务调度。

Redis、Celery、对象存储、MCP、pgvector 和额外 provider 包由具体应用的需求引入。可选示例的依赖单独声明，不随基础项目全部安装。

## 5. 对“任意 AI 应用”的具体支持方式

业务模块使用自己的 Pydantic 输入输出、FastAPI 路由和 Vue 页面：

| 业务类型 | 输入与输出 | 推荐实现 |
| --- | --- | --- |
| 对话助手 | 消息 → 文本/工具结果 | Agent 或对话图 + 对话组件 |
| 信息抽取 | 文本/文件引用 → 结构化对象 | 模型结构化输出 + 表单/结果表格 |
| RAG 问答 | 问题/文档引用 → 回答与来源 | 检索节点 + 生成节点 + 引用组件 |
| 自动化 Agent | 任务参数 → 执行进度与业务结果 | `create_agent` 或自定义图，工具调用进入业务服务 |
| 人工审批流程 | 任务 → 审批请求 → 继续执行 | LangGraph interrupt/resume + 审批页面 |
| 多模态应用 | 文件引用与参数 → 文件/结构化结果 | 官方多模态接口或供应商 SDK + 对应业务页面 |

大文件通过上传/对象存储传递引用，不放入统一 JSON 请求。多模态示例需要供应商与文件服务选择，第一版提供扩展说明，不宣称默认具备所有多模态功能。

共享的是调用生命周期和展示组件，业务输入输出不限制为 `messages` 或字符串。纯业务 API 可以直接使用 FastAPI，图 API 也可以保留领域路由，不强制汇入 `/apps/{id}/runs`。

## 6. 流式通信：复用官方协议，保持后端范围可控

调研发现：官方前端 SDK 当前已支持 Vue 的 `useStream`，覆盖消息、状态、工具生命周期、人工中断等；LangGraph 新应用文档推荐 event streaming。

实施前需要一个很小的接入验证：

1. 核实 Python LangGraph 稳定版本与 Vue SDK 的协议和版本兼容。
2. 验证官方 Vue SDK 能否用受支持的 transport 接入自有 FastAPI，而无需引入完整 Agent Server。
3. 验证一次结构化结果、工具调用、人工中断恢复与取消的端到端行为。

验证成功则直接复用 SDK，不再维护自研 Vue 运行状态框架。若官方接入要求超出轻量范围，使用原生 `fetch` 读取 SSE，并在网络边界做最小事件适配。该取舍必须记录验证结果，不能把“官方有 Vue SDK”直接等同于“当前自有后端可以无配置接入”。

SSE 是服务端推送传输；POST 请求可由 `fetch` 读取，不能默认使用仅支持 GET 的原生 EventSource 完成所有交互。SDK 的 Agent Server 运行重连等能力也不能在普通请求内执行模式下直接承诺。

后端只发给用户需要的结果、工具状态和进度。图内部状态、完整提示词、原始异常及内部推理不能无筛选直接透传浏览器。

“取消当前请求”与“持久化后台任务终止”是不同能力。默认实现请求级运行；在需要断线续跑、跨设备重连和可靠后台执行时，重新评估 Agent Server 或专门任务执行设施。checkpointer 本身不等于后台任务队列。

## 7. 建议目录

FastAPI 官方推荐使用 Python 包、`APIRouter` 和依赖注入组织较大的应用，但没有规定唯一的 `services`、`modules` 或 ORM 目录。LangGraph 官方展示了将 graph 与 state、nodes、tools 等代码分开组织的方式，也允许按项目调整结构。因此，下面采用常见的“按业务模块组织，模块内部区分职责”方式，是本脚手架的工程约定，不宣称是行业唯一标准。

FastAPI 接口与 AI 编排应有明确的代码边界，仍属于同一个 Python 后端工程，共享依赖、生命周期和部署。每个业务模块将自己的编排放在 `workflow/`，便于修改一个功能时同时找到接口、schema、业务逻辑和图。公共 `ai/` 只放跨业务的模型配置和运行集成，不集中存放全部业务工作流。

```text
backend/
  app/
    main.py                FastAPI 入口、路由组装、生命周期
    core/
      config.py            环境配置
      security.py          身份依赖及公共认证能力
      logging.py           请求/运行日志配置
      exceptions.py        公共异常与 HTTP 错误映射
    db/
      session.py           数据库引擎、会话与生命周期
    ai/
      model.py             官方模型配置与创建
      checkpoint.py        官方 checkpointer 初始化
      streaming.py         运行事件到前端传输的边界适配
    modules/
      auth/                最小身份与当前用户
      document_analysis/   示例业务模块，其他模块按相同原则组织
        router.py          HTTP 路由、请求响应与身份依赖
        schemas.py         API 输入输出的 Pydantic schema
        service.py         业务用例、权限规则与流程调用，按需拆分
        models.py          业务 ORM 模型，仅在需要持久化时建立
        workflow/
          graph.py         图/Agent 构建、节点连接与执行入口
          state.py         图内部状态，与 HTTP schema 分开
          nodes.py         节点逻辑
          tools.py         该业务使用的 LangChain 工具
          prompts.py       该业务提示词
  tests/                   按业务模块组织测试
  migrations/              Alembic 迁移
  pyproject.toml
frontend/
  src/
    api/                   OpenAPI 客户端及少量传输代码
    components/ai/         消息、工具、引用与结果展示组件
    layouts/
    router/
    stores/                仅共享状态
    views/                 按业务模块组织
examples/                  可复制的 RAG、工具与人工审批示例
docs/
compose.yaml
```

### 7.1 三层职责及依赖方向

| 位置 | 负责 | 边界 |
| --- | --- | --- |
| `router.py` | HTTP 输入输出、参数校验、当前用户依赖、调用业务用例 | 不堆放图节点、提示词和工具定义 |
| `service.py` | 业务规则、资源归属、存储及调用编排 | 逻辑简单时可省略；不用创建只有一行转发的 Service 类 |
| `workflow/graph.py` | LangChain Agent 或 LangGraph 的构建与编排 | 不依赖 FastAPI 的 Request、Response、HTTPException |
| `workflow/state.py` | 内部运行状态、状态合并规则 | 与公开 API schema 职责不同；根据业务显式映射 |
| `workflow/nodes.py`、`tools.py`、`prompts.py` | 节点、工具及模型任务定义 | 属于具体业务，不因代码涉及 AI 就搬到公共目录 |
| `ai/` | 模型、状态存储和传输的公共集成 | 不包装一套新的 Agent、Graph、Tool 或 Memory 接口 |

一般调用方向为 `router → service（需要时）→ workflow → 官方模型/工具`。编排只接收普通 Python 数据及执行上下文，通过公开结果或事件返回；HTTP 适配在接口边界完成。工具可以调用业务数据操作与外部 API，但不得递归调用用于启动自身的编排入口。用户身份由后端确定，不能仅信任前端传入的 user_id。

### 7.2 控制目录规模

上面的树说明文件位置，不要求每个模块预生成全部文件。单节点流程可以先只有 `workflow/graph.py`，提示词和小节点就近定义；节点增多或需要独立测试时才拆 `state.py`、`nodes.py` 等。共享配置等只有少量代码时也可以合并，不为文件名搭建空壳。

不默认增加 `repositories/`、`interfaces/`、`factories/`、通用 CRUD 基类或全局工具注册中心。业务确实多处复用的工具或节点才提取到公共模块。

将所有后端接口放在一棵目录、所有图放在另一棵目录也是可行的分层方式，但当前目标是团队与 AI 编程工具围绕具体业务功能同时修改三层代码，按业务聚合通常更便于定位，也更容易删除示例和复制新模块。只有出现独立部署、独立团队维护或特殊执行环境的实际需要，才考虑拆分编排服务。

图仍按官方 Python 模块组织，可以导出 compiled graph；以后需要官方部署时再添加 `langgraph.json`。不把官方部署配置误作为普通 FastAPI 项目运行的必需项。

## 8. 模板交付方式与升级边界

首版建议直接使用仓库模板或复制代码，提供清晰的项目名称、配置、示例删除和启动步骤。创建项目后，按第 1.1 节与 AI 编程工具协作，直接修改三层业务代码；无需先开发一套脚手架 CLI 或包管理平台。

每个派生项目独立维护业务代码与发布周期。上游脚手架记录版本、变更日志和迁移说明；“复制模板”不会自动同步上游更新。生成参数和初始化步骤确实反复增加时，可采用 Copier 等成熟工具。多个项目已经出现稳定的公共模块后，再考虑抽成独立依赖包。

## 9. 首版范围与验收

建议默认交付：

1. 最小登录、PostgreSQL 与迁移、资源归属隔离、前端基础布局。
2. 官方模型配置、图状态持久化、必要的流式通信集成。
3. 两个实际可运行的业务模块：对话助手、结构化抽取。
4. 可复制的工具 Agent、最小 RAG、人工中断恢复示例，依赖按示例安装。
5. OpenAPI 客户端、必要测试、Compose、CI、AI 编程工具规则和三层协作开发说明。

验收关注：

- 从模板创建独立项目，完成名称/配置替换、启动并删除不需要的示例。
- Trae/Codex 能通过已配置的项目规则识别三层修改位置和验证命令；需求确认后，以一个新增功能实测规则与示例是否足够。
- 新增一个表单型 AI 功能，只修改业务模块与对应页面，不修改公共 AI 层。
- 直接使用 `create_agent` 和自定义 `StateGraph`，不需要继承自研基类。
- 结构化输出保持 schema 约束；工具调用权限由服务端业务规则控制。
- 同一 thread 的会话在服务重启后可继续；另一个用户不能访问或恢复它。
- 多个请求不能并发错误更新同一 thread；初版明确单实例并发策略，不能将进程内锁宣传为多实例隔离。
- 流式失败、取消和人工中断均有明确终止或暂停状态；内部节点不会泄露敏感输出。
- 无模型密钥时能用测试替身检查工程链路；真实供应商行为另行验证。
- 默认部署只需前端静态服务、后端和 PostgreSQL，不依赖 Redis、向量库、队列或云追踪平台。
- Docker 开发环境能够修改代码并热更新；生产镜像可构建并启动，Python 运行时为 3.13，pnpm 在构建中使用配置的镜像源。

## 10. 与现有原型的关系

现有代码是未经方案确认的对话原型，不作为本方案的架构约束。

可复用部分是基础配置、输入校验、错误处理与流式解析测试。需要重新评估固定消息输入、手动写 token 事件、仅客户端会话状态、统一应用目录和工作台作为全部应用入口等选择。

调研阶段仅新增方案文档；用户随后明确授权开始实现。当前工程已替换原对话原型，
按本方案的业务目录、默认登录与 PostgreSQL、Docker、Python 3.13 和 pnpm 镜像要求实施。

## 11. 实施默认选择

建议采用 **FastAPI + Vue 3 + 官方 LangChain/LangGraph，默认带最小登录和 PostgreSQL，以独立业务项目模板交付**。

登录与 PostgreSQL 会增加少量工程代码及一个数据库服务，但能让团队复用身份隔离、业务存储和图状态恢复，避免每个应用重新封装。若团队大多数项目是无状态内部工具且已有统一网关身份，这两项可以改为可复制示例，而非默认模块。

用户随后指示“开始实现代码”，实施采用上述默认推荐选择。具体实现及运行边界见 README.md。

调研文档记录的是授权前的建议过程；后续明确实现指令已满足开始实施的条件。

用户同时已明确 Docker 管理项目、Python 3.13 和 pnpm 镜像安装要求，见第 3.1 节。这些要求无需再次确认。

## 官方参考资料

1. [FastAPI Full Stack Template](https://fastapi.tiangolo.com/project-generation/)：工程模板的认证、数据库、客户端、测试与部署范围。
2. [LangGraph Application structure](https://docs.langchain.com/oss/python/langgraph/application-structure)：图应用模块与部署配置。
3. [LangChain Models](https://docs.langchain.com/oss/python/langchain/models)：模型初始化、工具调用、结构化输出及多模态接口。
4. [LangChain Agents](https://docs.langchain.com/oss/python/langchain/agents)：`create_agent`、工具与结构化输出。
5. [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)：checkpointer 与 store 的职责。
6. [LangGraph Event streaming](https://docs.langchain.com/oss/python/langgraph/event-streaming)：当前新应用推荐的事件接口。
7. [LangChain Frontend overview](https://docs.langchain.com/oss/javascript/langchain/frontend/overview)：Vue 等前端 SDK 与 Agent UI 能力。
8. [Agent Server standalone deployment](https://docs.langchain.com/langsmith/deploy-standalone-server)：独立部署的运行组件与许可配置。
9. [Dify Docker Compose](https://docs.dify.ai/en/self-host/quick-start/docker-compose)：官方平台部署的服务构成。
10. [Langflow overview](https://docs.langflow.org/)：可视化流程、组件与应用开发方式。
11. [FastAPI Bigger Applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/)：Python 包、`APIRouter` 与跨模块依赖的官方组织示例。
