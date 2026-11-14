from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from backend.app.ai.streaming import stream_response
from backend.app.core.security import AuthenticatedUser, Session
from backend.app.modules.document_analysis.models import Analysis
from backend.app.modules.document_analysis.schemas import AnalysisInfo, AnalysisInput, ReviewInput
from backend.app.modules.document_analysis.service import analysis_info, config, run_analysis
from backend.app.modules.threads.models import Thread
from backend.app.modules.threads.service import claim_thread, owned_thread

router = APIRouter(prefix="/api/analyses", tags=["document_analysis"])


@router.post("", response_model=AnalysisInfo, status_code=201)
async def create_analysis(
    body: AnalysisInput,
    user: AuthenticatedUser,
    session: Session,
    request: Request,
):
    thread = Thread(user_id=user.id, module="analysis", title=body.text[:80])
    session.add(thread)
    await session.flush()
    analysis = Analysis(id=thread.id, text=body.text, require_review=body.require_review)
    session.add(analysis)
    await session.commit()
    return await analysis_info(request.app.state.analysis, thread, analysis)


@router.get("", response_model=list[AnalysisInfo])
async def list_analyses(user: AuthenticatedUser, session: Session, request: Request):
    rows = (
        await session.execute(
            select(Thread, Analysis)
            .join(Analysis)
            .where(
                Thread.user_id == user.id,
                Thread.module == "analysis",
            )
            .order_by(Thread.created_at.desc())
            .limit(50)
        )
    ).all()
    return [
        await analysis_info(request.app.state.analysis, thread, analysis)
        for thread, analysis in rows
    ]


@router.get("/{analysis_id}", response_model=AnalysisInfo)
async def get_analysis(
    analysis_id: UUID,
    user: AuthenticatedUser,
    session: Session,
    request: Request,
):
    thread = await owned_thread(session, analysis_id, user.id, "analysis")
    return await analysis_info(
        request.app.state.analysis,
        thread,
        await session.get(Analysis, analysis_id),
    )


@router.post("/{analysis_id}/run", response_class=StreamingResponse)
async def start_analysis(
    analysis_id: UUID,
    user: AuthenticatedUser,
    session: Session,
    request: Request,
):
    await owned_thread(session, analysis_id, user.id, "analysis")
    lock = await claim_thread(request.app.state.engine, analysis_id)
    try:
        state = await request.app.state.analysis.aget_state(config(analysis_id))
        if state.interrupts:
            raise HTTPException(409, "记录等待审核，请审核结果")
        analysis = await session.get(Analysis, analysis_id)
    except BaseException:
        await lock.close()
        raise
    return stream_response(
        request,
        analysis_id,
        lock,
        lambda: run_analysis(
            request.app.state.analysis,
            request.app.state.sessions,
            analysis,
        ),
    )


@router.post("/{analysis_id}/resume", response_class=StreamingResponse)
async def resume_analysis(
    analysis_id: UUID,
    body: ReviewInput,
    user: AuthenticatedUser,
    session: Session,
    request: Request,
):
    await owned_thread(session, analysis_id, user.id, "analysis")
    lock = await claim_thread(request.app.state.engine, analysis_id)
    try:
        state = await request.app.state.analysis.aget_state(config(analysis_id))
        if not state.interrupts:
            raise HTTPException(409, "此记录没有待审核结果")
        analysis = await session.get(Analysis, analysis_id)
    except BaseException:
        await lock.close()
        raise
    return stream_response(
        request,
        analysis_id,
        lock,
        lambda: run_analysis(
            request.app.state.analysis,
            request.app.state.sessions,
            analysis,
            body.approved,
        ),
    )
