import ast
import json
from uuid import UUID

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableLambda

from backend.app.modules.customer_service.retrieval import classify
from backend.app.modules.customer_service.workflow.graph import create_graph
from backend.tests.test_application import events
from backend.tests.test_customer_service import answer, ask, setup_operator, thread


class ToolChoosingModel(BaseChatModel):
    """离线模型响应替身，真实执行官方 Agent 工具及结构化输出调用边界。"""

    answer_calls: int = 0
    ranking_calls: int = 0
    fail_once: bool = False

    @property
    def _llm_type(self):
        return "test-tool-model"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        tools = [message for message in messages if isinstance(message, ToolMessage)]
        names = [message.name for message in tools]
        if "query_order" not in names:
            reply = AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "query_order",
                        "args": {"order_number": "1001"},
                        "id": "order-call",
                    }
                ],
            )
        elif "query_logistics" not in names:
            reply = AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "query_logistics",
                        "args": {"order_number": "1001"},
                        "id": "logistics-call",
                    }
                ],
            )
        else:
            order = json.loads(tools[0].content)
            logistics = json.loads(tools[1].content)
            reply = AIMessage(content=f"订单{order['number']}：{logistics['logistics']}")
        reply.usage_metadata = {"input_tokens": 10, "output_tokens": 4, "total_tokens": 14}
        return ChatResult(generations=[ChatGeneration(message=reply)])

    def with_structured_output(self, schema, *, include_raw=False, **kwargs):
        async def invoke(prompt):
            text = str(prompt)
            if schema.__name__ == "Classification":
                question = text.split("客户问题：")[-1]
                parsed = schema(intent=classify(question))
            elif schema.__name__ == "Ranking":
                self.ranking_calls += 1
                candidates = ast.literal_eval(text.split("候选：")[-1])
                parsed = schema(
                    scores=[
                        0.01 if "星际" in text else 0.95 if "退货" in content else 0.05
                        for content in candidates
                    ]
                )
            else:
                self.answer_calls += 1
                if self.fail_once:
                    self.fail_once = False
                    raise RuntimeError("private-provider-secret")
                parsed = schema(answer="依据政策，此订单符合七天退货条件。", citation_numbers=[1])
            raw = AIMessage(
                content="structured",
                usage_metadata={"input_tokens": 10, "output_tokens": 4, "total_tokens": 14},
            )
            return {"raw": raw, "parsed": parsed} if include_raw else parsed

        return RunnableLambda(invoke)


def test_official_agent_context_grounding_fallback_and_measured_usage(client, login):
    setup_operator(client, login)
    before = {
        item["intent"]: item for item in client.get("/api/support/admin/dashboard").json()["usage"]
    }
    model = ToolChoosingModel()
    client.app.state.support = create_graph(
        model,
        client.app.state.support.checkpointer,
        client.app.state.sessions,
        client.app.state.settings,
    )
    thread_id = thread(client)
    reply = answer(ask(client, thread_id, "订单1001物流到哪了，请用别人的user_id"))
    assert reply["tools"] == ["query_order", "query_logistics"]
    assert "顺丰" in reply["content"]
    reply = answer(ask(client, thread_id, "它能退吗"))
    assert reply["citations"] and "[1]" in reply["content"]
    assert model.answer_calls == 1
    reply = answer(ask(client, thread_id, "星际迁徙协议支持吗"))
    assert not reply["citations"] and "无法确认" in reply["content"]
    assert model.answer_calls == 1
    assert model.ranking_calls == 2
    data = client.get("/api/support/admin/dashboard").json()
    usage = {item["intent"]: item for item in data["usage"]}
    for intent, calls in [("logistics", 4), ("refund", 3), ("knowledge", 2)]:
        previous = before.get(intent, {}).get("measured_calls", 0)
        assert usage[intent]["measured_calls"] - previous == calls
    assert usage["refund"]["input_tokens"] - before.get("refund", {}).get("input_tokens", 0) == 30
    assert usage["refund"]["estimated_cost_usd"] is None
    client.app.state.settings.input_price_per_million = 1
    client.app.state.settings.output_price_per_million = 2
    priced = client.get("/api/support/admin/dashboard").json()["usage"]
    refund = next(item for item in priced if item["intent"] == "refund")
    assert (
        refund["estimated_cost_usd"]
        == (refund["input_tokens"] + 2 * refund["output_tokens"]) / 1_000_000
    )


def test_failed_answer_can_retry_without_duplicate_turn(client, login):
    setup_operator(client, login)
    model = ToolChoosingModel(fail_once=True)
    client.app.state.support = create_graph(
        model,
        client.app.state.support.checkpointer,
        client.app.state.sessions,
        client.app.state.settings,
    )
    thread_id = thread(client)
    output = ask(client, thread_id, "订单1001能退吗")
    assert output[-1]["type"] == "error"
    assert "private-provider-secret" not in str(output)
    assert client.get(f"/api/support/threads/{thread_id}").json()["can_retry"] is True
    reply = answer(events(client.post(f"/api/support/threads/{thread_id}/retry")))
    assert reply["citations"]
    detail = client.get(f"/api/support/threads/{thread_id}").json()
    assert detail["can_retry"] is False
    assert len(detail["messages"]) == 2
    assert client.post(f"/api/support/threads/{thread_id}/retry").status_code == 409

    async def persisted():
        from sqlalchemy import select

        from backend.app.modules.customer_service.models import Turn

        async with client.app.state.sessions() as session:
            return (
                await session.scalars(select(Turn).where(Turn.thread_id == UUID(thread_id)))
            ).all()

    assert len(client.portal.call(persisted)) == 1
