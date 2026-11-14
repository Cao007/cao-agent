import json

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from examples.tool_agent import Context, my_orders


class ToolModel(BaseChatModel):
    @property
    def _llm_type(self):
        return "test-tool-model"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        message = (
            AIMessage(content="查询完成")
            if isinstance(messages[-1], ToolMessage)
            else AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "my_orders",
                        "args": {},
                        "id": "call-1",
                        "type": "tool_call",
                    }
                ],
            )
        )
        return ChatResult(generations=[ChatGeneration(message=message)])


def test_official_agent_tool_runtime_filters_by_server_context():
    agent = create_agent(ToolModel(), tools=[my_orders], context_schema=Context)
    assert my_orders.args == {}  # user_id 不进入模型可填写的参数。
    for user_id, expected in [
        ("demo-user", [{"id": "order-001", "status": "shipped"}]),
        ("another-user", []),
    ]:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": "查询订单"}]},
            context=Context(user_id=user_id),
        )
        tool_result = next(m for m in result["messages"] if isinstance(m, ToolMessage))
        assert json.loads(tool_result.content) == {"orders": expected}
