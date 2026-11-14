from langgraph.types import Command
from sqlalchemy import update

from backend.app.modules.document_analysis.models import Analysis
from backend.app.modules.document_analysis.schemas import AnalysisInfo, Extraction


def config(analysis_id):
    return {"configurable": {"thread_id": str(analysis_id)}}


async def analysis_info(graph, thread, analysis):
    snapshot = await graph.aget_state(config(thread.id))
    pending = bool(snapshot.interrupts)
    return AnalysisInfo(
        id=thread.id,
        title=thread.title,
        status="paused" if pending else thread.status,
        text=analysis.text,
        require_review=analysis.require_review,
        result=analysis.result,
        review=snapshot.values.get("candidate") if pending else None,
    )


async def run_analysis(graph, sessions, analysis, resume: bool | None = None):
    before = await graph.aget_state(config(analysis.id))
    initial = (
        Command(resume=resume)
        if resume is not None
        else {"source": analysis.text, "require_review": analysis.require_review}
    )
    if "approved" not in before.values:
        # 已启动的非暂停流程用 None 恢复失败节点，避免重跑已完成的抽取。
        if resume is None and before.values:
            initial = None
        # updates 只用于进度名称；不把节点输出和原始输入透传给浏览器。
        async for update_event in graph.astream(
            initial, config(analysis.id), stream_mode="updates"
        ):
            if "extract" in update_event:
                yield {"type": "progress", "message": "抽取完成"}
    snapshot = await graph.aget_state(config(analysis.id))
    if snapshot.interrupts:
        candidate = Extraction.model_validate(snapshot.values["candidate"])
        yield {"type": "paused", "review": candidate.model_dump()}
        return
    result = (
        Extraction.model_validate(snapshot.values["candidate"]).model_dump()
        if snapshot.values.get("approved")
        else None
    )
    async with sessions() as session:
        await session.execute(
            update(Analysis).where(Analysis.id == analysis.id).values(result=result)
        )
        await session.commit()
    yield {"type": "result", "result": result}
    yield {"type": "done"}
