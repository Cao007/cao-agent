"""无模型密钥可运行的官方 interrupt/resume 检查；生产示例见 document_analysis。"""

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from typing_extensions import TypedDict


class State(TypedDict, total=False):
    proposal: str
    approved: bool


def review(state: State):
    return {"approved": interrupt({"proposal": state["proposal"]})}


graph = (
    StateGraph(State)
    .add_node("review", review)
    .add_edge(START, "review")
    .add_edge("review", END)
    .compile(checkpointer=InMemorySaver())
)


if __name__ == "__main__":
    config = {"configurable": {"thread_id": "example-review"}}
    paused = graph.invoke({"proposal": "发布已审核的摘要"}, config)
    assert paused["__interrupt__"]
    result = graph.invoke(Command(resume=True), config)
    assert result["approved"] is True
    print(result)
