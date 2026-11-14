from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from backend.app.modules.document_analysis.schemas import Extraction
from backend.app.modules.document_analysis.workflow.state import AnalysisState


def create_graph(model, checkpointer):
    structured = model.with_structured_output(Extraction) if model else None

    async def extract(state: AnalysisState):
        if structured is None:
            result = Extraction(
                title="演示抽取结果",
                summary=state["source"][:200],
                key_points=["演示模式只截取原文，不执行语义抽取。"],
                action_items=["配置真实模型后验证抽取质量。"],
            )
        else:
            result = await structured.ainvoke(
                [
                    SystemMessage(
                        content="从原文提取标题、摘要、要点和行动项。"
                        "仅依据原文，缺少的信息用空列表表示。"
                    ),
                    HumanMessage(content=state["source"]),
                ]
            )
            result = Extraction.model_validate(result)
        return {"candidate": result.model_dump()}

    def review(state: AnalysisState):
        # interrupt 前不可写业务数据：恢复时此节点会从头执行。
        approved = interrupt({"candidate": state["candidate"]}) if state["require_review"] else True
        return {"approved": bool(approved)}

    return (
        StateGraph(AnalysisState)
        .add_node("extract", extract)
        .add_node("review", review)
        .add_edge(START, "extract")
        .add_edge("extract", "review")
        .add_edge("review", END)
        .compile(checkpointer=checkpointer)
    )
