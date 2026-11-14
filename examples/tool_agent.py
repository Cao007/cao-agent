"""直接使用官方 create_agent；工具权限在服务端决定，不让模型选择任意用户。"""

import asyncio
from dataclasses import dataclass

from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool

from backend.app.ai.model import create_model
from backend.app.core.config import Settings


@dataclass(frozen=True)
class Context:
    user_id: str


@tool
def my_orders(runtime: ToolRuntime[Context]) -> dict:
    """查询当前用户的订单。"""
    # 真实业务在此调用按 user_id 过滤的服务；user_id 不在模型可填写的工具参数内。
    records = [{"id": "order-001", "user_id": "demo-user", "status": "shipped"}]
    return {
        "orders": [
            {"id": r["id"], "status": r["status"]}
            for r in records
            if r["user_id"] == runtime.context.user_id
        ]
    }


async def main():
    model = create_model(Settings())
    if model is None:
        raise SystemExit("工具 Agent 需要 MODEL_MODE=openai 与模型密钥")
    agent = create_agent(
        model,
        tools=[my_orders],
        context_schema=Context,
        system_prompt="查询当前用户订单，禁止编造订单状态。",
    )
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "查询我的订单"}]},
        context=Context(user_id="demo-user"),
    )
    print(result["messages"][-1].text)


if __name__ == "__main__":
    asyncio.run(main())
