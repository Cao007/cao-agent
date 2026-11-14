from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from backend.app.ai.streaming import stream_response
from backend.app.core.security import AuthenticatedUser, Session
from backend.app.modules.chat.schemas import ChatInput, ThreadCreate, ThreadInfo
from backend.app.modules.chat.service import config
from backend.app.modules.customer_service.models import EvaluationCase, Knowledge, Operator, Turn
from backend.app.modules.customer_service.retrieval import index_knowledge
from backend.app.modules.customer_service.schemas import (
    Dashboard,
    EvaluationInfo,
    EvaluationInput,
    EvaluationResult,
    FeedbackInput,
    KnowledgeInfo,
    KnowledgeInput,
    OrderInfo,
    OrderSelection,
    ReviewInput,
    SupportProfile,
    SupportThread,
    TurnInfo,
)
from backend.app.modules.customer_service.service import (
    dashboard,
    evaluate,
    knowledge_info,
    public_messages,
    run_support,
)
from backend.app.modules.customer_service.workflow.graph import owned_orders
from backend.app.modules.threads.models import Thread
from backend.app.modules.threads.service import claim_thread, owned_thread

router = APIRouter(prefix="/api/support", tags=["customer_service"])


async def require_operator(user: AuthenticatedUser, session: Session):
    if await session.get(Operator, user.id) is None:
        raise HTTPException(403, "需要客服运营权限")
    return user


Staff = Annotated[object, Depends(require_operator)]


@router.get("/profile", response_model=SupportProfile)
async def profile(user: AuthenticatedUser, session: Session, request: Request):
    return SupportProfile(
        is_operator=await session.get(Operator, user.id) is not None,
        mode=request.app.state.settings.model_mode,
        threshold=request.app.state.settings.support_threshold,
    )


@router.get("/orders", response_model=list[OrderInfo])
async def list_orders(user: AuthenticatedUser, request: Request):
    return await owned_orders(request.app.state.sessions, user.id)


@router.post("/demo-orders", response_model=list[OrderInfo])
async def demo_orders(user: AuthenticatedUser, session: Session, request: Request):
    if request.app.state.settings.model_mode != "demo":
        raise HTTPException(404, "演示入口未启用")
    from backend.app.modules.customer_service.seed import seed_orders

    await seed_orders(session, user.id)
    await session.commit()
    return await owned_orders(request.app.state.sessions, user.id)


@router.get("/threads", response_model=list[ThreadInfo])
async def threads(user: AuthenticatedUser, session: Session):
    return (
        await session.scalars(
            select(Thread)
            .where(Thread.user_id == user.id, Thread.module == "customer_service")
            .order_by(Thread.created_at.desc())
            .limit(100)
        )
    ).all()


@router.post("/threads", response_model=ThreadInfo, status_code=201)
async def create_thread(body: ThreadCreate, user: AuthenticatedUser, session: Session):
    thread = Thread(user_id=user.id, module="customer_service", title=body.title)
    session.add(thread)
    await session.commit()
    return thread


@router.get("/threads/{thread_id}", response_model=SupportThread)
async def detail(thread_id: UUID, user: AuthenticatedUser, session: Session, request: Request):
    thread = await owned_thread(session, thread_id, user.id, "customer_service")
    state = await request.app.state.support.aget_state(config(thread_id))
    return SupportThread(
        **ThreadInfo.model_validate(thread).model_dump(),
        messages=await public_messages(session, state, user.id),
        orders_to_select=state.interrupts[0].value["orders"] if state.interrupts else [],
        can_retry=bool(state.next) and not bool(state.interrupts),
    )


async def start_run(thread_id, user, session, request, text=None, selection=None, retry=False):
    await owned_thread(session, thread_id, user.id, "customer_service")
    lock = await claim_thread(request.app.state.engine, thread_id)
    try:
        graph = request.app.state.support
        state = await graph.aget_state(config(thread_id))
        if retry:
            if not state.next or state.interrupts:
                raise HTTPException(409, "没有可以重试的流程；中断时请选择订单")
        elif selection is not None:
            if not state.interrupts:
                raise HTTPException(409, "此会话没有待选择的订单")
            allowed = {order["id"] for order in state.interrupts[0].value["orders"]}
            actual = {
                order["id"] for order in await owned_orders(request.app.state.sessions, user.id)
            }
            if str(selection) not in allowed & actual:
                raise HTTPException(422, "请选择本次待确认的本人订单")
        elif state.next:
            raise HTTPException(409, "请先完成待处理流程；中断时请选择订单")
        return stream_response(
            request,
            thread_id,
            lock,
            lambda: run_support(
                graph, request.app.state.sessions, thread_id, user.id, text, selection, retry
            ),
        )
    except BaseException:
        await lock.close()
        raise


@router.post("/threads/{thread_id}/messages", response_class=StreamingResponse)
async def send(
    thread_id: UUID, body: ChatInput, user: AuthenticatedUser, session: Session, request: Request
):
    return await start_run(thread_id, user, session, request, text=body.message)


@router.post("/threads/{thread_id}/resume", response_class=StreamingResponse)
async def resume(
    thread_id: UUID,
    body: OrderSelection,
    user: AuthenticatedUser,
    session: Session,
    request: Request,
):
    return await start_run(thread_id, user, session, request, selection=body.order_id)


@router.post("/threads/{thread_id}/retry", response_class=StreamingResponse)
async def retry(thread_id: UUID, user: AuthenticatedUser, session: Session, request: Request):
    return await start_run(thread_id, user, session, request, retry=True)


async def owned_turn(session, turn_id, user_id):
    turn = await session.scalar(
        select(Turn).where(Turn.id == turn_id, Turn.user_id == user_id).with_for_update()
    )
    if turn is None:
        raise HTTPException(404, "回答不存在")
    return turn


@router.post("/turns/{turn_id}/feedback", response_model=TurnInfo)
async def feedback(turn_id: UUID, body: FeedbackInput, user: AuthenticatedUser, session: Session):
    turn = await owned_turn(session, turn_id, user.id)
    turn.feedback = body.value
    if body.value == "down" and turn.review_status is None:
        turn.review_status = "pending"
    await session.commit()
    return turn


@router.post("/turns/{turn_id}/handoff", response_model=TurnInfo)
async def handoff(turn_id: UUID, user: AuthenticatedUser, session: Session):
    turn = await owned_turn(session, turn_id, user.id)
    turn.handoff = True
    if turn.review_status is None:
        turn.review_status = "pending"
    await session.commit()
    return turn


@router.get("/admin/dashboard", response_model=Dashboard)
async def overview(staff: Staff, session: Session, request: Request):
    return await dashboard(session, request.app.state.settings)


@router.get("/admin/knowledge", response_model=list[KnowledgeInfo])
async def knowledge_list(staff: Staff, session: Session):
    return [
        knowledge_info(item)
        for item in (await session.scalars(select(Knowledge).order_by(Knowledge.title))).all()
    ]


@router.post("/admin/knowledge", response_model=KnowledgeInfo, status_code=201)
async def knowledge_create(body: KnowledgeInput, staff: Staff, session: Session, request: Request):
    item = Knowledge(**body.model_dump())
    await index_knowledge(item, request.app.state.settings)
    session.add(item)
    await session.commit()
    return knowledge_info(item)


@router.put("/admin/knowledge/{knowledge_id}", response_model=KnowledgeInfo)
async def knowledge_update(
    knowledge_id: UUID, body: KnowledgeInput, staff: Staff, session: Session, request: Request
):
    item = await session.get(Knowledge, knowledge_id, with_for_update=True)
    if item is None:
        raise HTTPException(404, "知识不存在")
    for key, value in body.model_dump().items():
        setattr(item, key, value)
    await index_knowledge(item, request.app.state.settings)
    await session.commit()
    return knowledge_info(item)


@router.post("/admin/knowledge/{knowledge_id}/archive", response_model=KnowledgeInfo)
async def archive(knowledge_id: UUID, staff: Staff, session: Session):
    item = await session.get(Knowledge, knowledge_id, with_for_update=True)
    if item is None:
        raise HTTPException(404, "知识不存在")
    item.status = "archived"
    await session.commit()
    return knowledge_info(item)


@router.get("/admin/reviews", response_model=list[TurnInfo])
async def reviews(staff: Staff, session: Session):
    return (
        await session.scalars(
            select(Turn)
            .where(Turn.review_status.is_not(None))
            .order_by(Turn.created_at.desc())
            .limit(200)
        )
    ).all()


@router.post("/admin/reviews/{turn_id}", response_model=TurnInfo)
async def review(
    turn_id: UUID, body: ReviewInput, staff: Staff, session: Session, request: Request
):
    turn = await session.get(Turn, turn_id, with_for_update=True)
    if turn is None:
        raise HTTPException(404, "待审记录不存在")
    if turn.review_status != "pending":
        raise HTTPException(409, "此记录已审核")
    if body.action == "approve":
        if not body.answer.strip():
            raise HTTPException(422, "审核通过需要填写可靠答案")
        item = Knowledge(
            title=turn.question[:120],
            content=body.answer,
            category="refund" if turn.intent == "refund" else "faq",
        )
        await index_knowledge(item, request.app.state.settings)
        session.add(item)
        turn.correction = body.answer
    turn.review_status = {"approve": "approved", "reject": "rejected", "expire": "expired"}[
        body.action
    ]
    await session.commit()
    return turn


@router.get("/admin/evaluation-cases", response_model=list[EvaluationInfo])
async def evaluation_cases(staff: Staff, session: Session):
    return (await session.scalars(select(EvaluationCase).order_by(EvaluationCase.id))).all()


@router.post("/admin/evaluation-cases", response_model=EvaluationInfo, status_code=201)
async def add_case(body: EvaluationInput, staff: Staff, session: Session):
    if (
        body.expected_knowledge_id
        and await session.get(Knowledge, body.expected_knowledge_id) is None
    ):
        raise HTTPException(422, "预期知识不存在")
    item = EvaluationCase(**body.model_dump())
    session.add(item)
    await session.commit()
    return item


@router.put("/admin/evaluation-cases/{case_id}", response_model=EvaluationInfo)
async def update_case(case_id: UUID, body: EvaluationInput, staff: Staff, session: Session):
    item = await session.get(EvaluationCase, case_id)
    if item is None:
        raise HTTPException(404, "评估题不存在")
    if (
        body.expected_knowledge_id
        and await session.get(Knowledge, body.expected_knowledge_id) is None
    ):
        raise HTTPException(422, "预期知识不存在")
    for key, value in body.model_dump().items():
        setattr(item, key, value)
    await session.commit()
    return item


@router.post("/admin/evaluate", response_model=EvaluationResult)
async def run_evaluation(staff: Staff, request: Request):
    try:
        return await evaluate(
            request.app.state.sessions, request.app.state.settings, request.app.state.support_model
        )
    except ValueError as error:
        if str(error) == "请先录入评估题":
            raise HTTPException(422, str(error)) from error
        raise
