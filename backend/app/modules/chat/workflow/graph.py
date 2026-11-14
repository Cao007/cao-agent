import asyncio

from langchain_core.messages import AIMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph


def create_graph(model, checkpointer):
    async def respond(state: MessagesState):
        # ponytail: 按最近 40 条及字符预算传模型，完整历史仍由 checkpointer 保存。
        history, length = [], 0
        for message in reversed(state["messages"][-40:]):
            length += len(str(message.content))
            if length > 64000:
                break
            history.insert(0, message)
        if model is None:
            await asyncio.sleep(0.15)
            text = (
                f"演示模式：已收到「{state['messages'][-1].content}」。\n"
                f"这段会话已保存，目前共有 {(len(state['messages']) + 1) // 2} 轮。"
                "\n配置真实模型后即可获得 AI 回答。"
            )
            return {"messages": [AIMessage(content=text)]}
        answer = await model.ainvoke(
            [
                SystemMessage(content="你是可靠的中文助手。回答具体，不确定时说明，不编造事实。"),
                *history,
            ]
        )
        return {"messages": [answer]}

    return (
        StateGraph(MessagesState)
        .add_node("respond", respond)
        .add_edge(START, "respond")
        .add_edge("respond", END)
        .compile(checkpointer=checkpointer)
    )
