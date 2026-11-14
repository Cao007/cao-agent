from langchain_core.messages import AIMessage, HumanMessage

from backend.app.modules.chat.schemas import Message


def config(thread_id):
    return {"configurable": {"thread_id": str(thread_id)}}


def public_messages(values: dict):
    return [
        Message(
            role="assistant" if isinstance(message, AIMessage) else "user", content=message.text
        )
        for message in values.get("messages", [])
        if isinstance(message, (HumanMessage, AIMessage))
    ]


async def run_chat(graph, thread_id, text):
    has_tokens = False
    async for chunk, metadata in graph.astream(
        {"messages": [HumanMessage(content=text)]},
        config(thread_id),
        stream_mode="messages",
    ):
        if metadata.get("langgraph_node") == "respond" and isinstance(chunk, AIMessage):
            for block in chunk.content_blocks:
                if block["type"] == "text":
                    has_tokens = True
                    yield {"type": "token", "content": block["text"]}
    state = await graph.aget_state(config(thread_id))
    messages = public_messages(state.values)
    if not messages or messages[-1].role != "assistant" or not messages[-1].content.strip():
        raise ValueError("Model did not return public text")
    if not has_tokens and messages and messages[-1].role == "assistant":
        yield {"type": "token", "content": messages[-1].content}
    yield {"type": "done"}
