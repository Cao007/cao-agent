from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from backend.app.ai.streaming import stream_response
from backend.app.core.security import AuthenticatedUser, Session
from backend.app.modules.chat.schemas import ChatInput, ThreadCreate, ThreadDetail, ThreadInfo
from backend.app.modules.chat.service import config, public_messages, run_chat
from backend.app.modules.threads.models import Thread
from backend.app.modules.threads.service import claim_thread, owned_thread

router = APIRouter(prefix="/api/chat/threads", tags=["chat"])


@router.get("", response_model=list[ThreadInfo])
async def list_threads(user: AuthenticatedUser, session: Session):
    return (
        await session.scalars(
            select(Thread)
            .where(
                Thread.user_id == user.id,
                Thread.module == "chat",
            )
            .order_by(Thread.created_at.desc())
            .limit(100)
        )
    ).all()


@router.post("", response_model=ThreadInfo, status_code=201)
async def create_thread(body: ThreadCreate, user: AuthenticatedUser, session: Session):
    thread = Thread(user_id=user.id, module="chat", title=body.title)
    session.add(thread)
    await session.commit()
    return thread


@router.get("/{thread_id}", response_model=ThreadDetail)
async def get_thread(thread_id: UUID, user: AuthenticatedUser, session: Session, request: Request):
    thread = await owned_thread(session, thread_id, user.id, "chat")
    state = await request.app.state.chat.aget_state(config(thread_id))
    return ThreadDetail(
        **ThreadInfo.model_validate(thread).model_dump(), messages=public_messages(state.values)
    )


@router.post("/{thread_id}/messages", response_class=StreamingResponse)
async def send_message(
    thread_id: UUID,
    body: ChatInput,
    user: AuthenticatedUser,
    session: Session,
    request: Request,
):
    await owned_thread(session, thread_id, user.id, "chat")
    lock = await claim_thread(request.app.state.engine, thread_id)
    return stream_response(
        request,
        thread_id,
        lock,
        lambda: run_chat(request.app.state.chat, thread_id, body.message),
    )
