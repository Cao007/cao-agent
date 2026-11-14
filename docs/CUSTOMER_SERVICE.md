# MewHelp 客服应用

基于飞书功能说明和 Cao AI 框架实现。需求边界见
[CUSTOMER_SERVICE_REQUIREMENTS.md](CUSTOMER_SERVICE_REQUIREMENTS.md)。
工作分支：`feat/ai-customer-service`。

## 启动与账号

```bash
cp .env.example .env
docker compose up -d --build
```

访问 http://127.0.0.1:8080 。注册账户后默认是普通客户。
普通客户只访问本人订单、会话和反馈，运营接口要求后端确认的运营身份。
在本地执行以下命令，显式为已注册的账户开通运营权限并初始化样例：

```bash
docker compose exec backend python -m backend.app.modules.customer_service.seed --operator 你的用户名
```

初始化包含 4 篇标注为演示的知识、9 道本项目手写评估题，以及本人 3 笔样例订单。
再次执行不会重复添加样例。其他客户可在演示模式点击“加载本人演示订单”。
修改知识或更换 embedding 模型后，在知识库“编辑 → 保存并索引”重新索引。

本次本机验收已创建运营账号 `mewhelp_demo`，密码 `MewHelp-demo-2026`，
并保留浏览器登录状态。这是本地演示账号，代码和迁移不预设此账号。
当前数据库还包含浏览器审核新增的演示知识和更新后的 10 道评估题。

页面：

- `/support`：客户咨询与本人订单。
- `/operations`：运营工作台；普通客户的后台请求返回 403。
- `/api/docs`：接口文档。

## 试用流程

1. 问“保温杯怎么清洗”，展开 `[1]` 查看实际知识片段。
2. 问“订单1001物流到哪了”，查看订单、物流工具记录。
3. 接着问“它能退吗”，核对仍关联到 1001，并引用七天退货政策。
4. 新会话问“我买的东西能退吗”，流程暂停；选择 1002 后继续，显示超期研判。
   刷新或重启后仍可点选恢复，不能选择其他客户的订单。
5. 问未收录问题；回答明确无法确认。点击“申请人工接管”创建应用内工单。
6. 运营后台“飞轮待审”补写可靠答案并通过，再次提问能检索到新增知识。
   点踩也会进入待审队列，支持驳回与过期处理。
7. 编辑评估题的预期知识和标注意图后，运行 RAG 评估，
   查看四种策略、分类器混淆统计及推荐阈值。

失败或停止时保留 checkpoint。重新加载后，未完成的节点可以“重试上次流程”；
订单中断必须通过订单选择恢复。重复恢复与重复审核返回 409。
退款功能仅做资格研判，不提交退款、不变更订单。
人工接管在应用内待审队列中体现，不向飞书或邮件发送消息。

## 真实模型配置

```dotenv
MODEL_MODE=openai
MODEL_NAME=gpt-4.1-mini
OPENAI_API_KEY=你的密钥
OPENAI_BASE_URL=https://api.openai.com/v1
EMBEDDING_MODEL=text-embedding-3-small
SUPPORT_THRESHOLD=0.38
```

```bash
docker compose up -d --force-recreate backend
```

真实模式使用官方 `init_chat_model`、`OpenAIEmbeddings` 和 `create_agent`。
供应商需要支持 embedding、工具调用与结构化输出。索引按 embedding 模型隔离；
演示索引不会被真实模式混用，切换后请重新保存需要启用的知识。
模型根据工具返回的本人订单和物流回答；退款由确定性图先查订单、再取政策，
最后生成带引用的研判。低检索分数在回答生成前进入兜底。

检索分数是门控指标，不是经过概率校准的正确率。
`SUPPORT_THRESHOLD` 应在真实业务评估集上选择；页面推荐值不会自动修改线上配置。
重排使用聊天模型对候选打分，当前没有单独的 cross-encoder 服务。

## 指标与已知边界

- 演示向量是字符哈希，演示重排奖励连续文本匹配，不代表真实语义能力。
  演示退款采用样例七天/未拆封规则；自定义政策研判需在真实模型模式验证。
- 当前检索扫描最多 500 篇知识，每篇按 600 字、80 字重叠切块；
  面向小规模验证，更多知识应换用 PostgreSQL pgvector 等索引。
- Recall@3 / MRR@3 只在有预期知识的题上计算。覆盖度统计全部检索题中
  超过当前阈值的比例；高覆盖不一定意味着高质量。
- 阈值推荐由同一小型评估集计算，尚未做独立验证集或概率校准。
  知识审核后应更新题目标注，并继续保留未知问题作为负例。
- 用量按完成的客服轮次统计，模型调用与 token 来自供应商 `usage_metadata`，
  包括分类、聊天重排、Agent 与回答。配置两个价格后显示聊天模型 USD 估算：
  `INPUT_PRICE_PER_MILLION`、`OUTPUT_PRICE_PER_MILLION`。
  无价格或无实测调用时为“未知”；不包含 embedding、索引与后台评估费用，
  也不作为供应商账单核对结果。
- SSE 发送公开进度，最终结构化回答经过引用校验后整体发送；
  不转发原始图状态、提示词、内部推理或供应商异常。
- 参考系统的原始 300 题未提供。本项目样例指标只能证明流程可运行。
  当前没有真实供应商密钥，真实模型、embedding 及重排效果尚未联网验收。
- 索引在保存请求内完成，进度为完成状态（0/100），没有后台任务队列。
  新增、更新、审核的知识与索引同事务提交，失败不会留下半成品。

## 验证命令

完整框架检查见根目录 README。客服关键测试在
`backend/tests/test_customer_service.py` 和 `test_customer_service_model.py`。
数据库需使用独立测试库并先迁移：

```bash
DATABASE_URL=postgresql://cao:cao@localhost:5432/cao_test uv run python -m backend.migrate
uv run ruff check backend examples
uv run ruff format --check backend examples
TEST_DATABASE_URL=postgresql://cao:cao@localhost:5432/cao_test uv run pytest -q
pnpm --dir frontend test
pnpm --dir frontend build
```

针对已经运行的 Docker 服务：

```bash
SUPPORT_USERNAME=你的运营用户名 SUPPORT_PASSWORD=你的密码 \
  uv run python -m backend.customer_service_acceptance
```

该验收会创建测试会话、普通客户及人工工单，运行评估，
生成 `docs/CUSTOMER_SERVICE_VERIFICATION.json`。本机示例中还同步浏览器审核后的题目标注。
生产 Docker 镜像不安装开发组 httpx；此脚本从主机的 uv 开发环境执行。
代码未创建 commit 或推送。
