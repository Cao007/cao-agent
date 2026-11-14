from collections import Counter, defaultdict
from datetime import UTC, datetime
from uuid import UUID, uuid4

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command
from sqlalchemy import select

from backend.app.modules.chat.service import config
from backend.app.modules.customer_service.models import (
    EvaluationCase,
    EvaluationRun,
    Knowledge,
    Turn,
)
from backend.app.modules.customer_service.retrieval import classify, retrieve
from backend.app.modules.customer_service.schemas import (
    Dashboard,
    EvaluationResult,
    IntentUsage,
    KnowledgeInfo,
    SupportMessage,
)


def knowledge_info(item):
    return KnowledgeInfo(
        id=item.id,
        title=item.title,
        content=item.content,
        category=item.category,
        status=item.status,
        index_mode=item.index_mode,
        chunk_count=len(item.chunks),
        progress=100 if item.status == "indexed" else 0,
    )


def message_info(turn):
    return SupportMessage(
        role="assistant",
        content=turn.answer,
        turn_id=turn.id,
        citations=turn.citations,
        tools=turn.tools,
        confidence=turn.confidence,
        feedback=turn.feedback,
        handoff=turn.handoff,
    )


async def public_messages(session, state, user_id):
    turns = (await session.scalars(select(Turn).where(Turn.user_id == user_id))).all()
    by_id = {str(turn.id): turn for turn in turns}
    result = []
    for message in state.values.get("messages", []):
        if isinstance(message, HumanMessage):
            result.append(SupportMessage(role="user", content=message.text))
        elif isinstance(message, AIMessage) and message.id in by_id:
            result.append(message_info(by_id[message.id]))
    return result


async def run_support(graph, sessions, thread_id, user_id, text=None, selection=None, retry=False):
    input_value = (
        None
        if retry
        else Command(resume=str(selection))
        if selection
        else {
            "messages": [HumanMessage(content=text)],
            "question": text,
            "user_id": str(user_id),
            "thread_id": str(thread_id),
            "turn_id": str(uuid4()),
        }
    )
    async for update in graph.astream(input_value, config(thread_id), stream_mode="updates"):
        for node in update:
            if node != "__interrupt__":
                yield {
                    "type": "progress",
                    "message": {
                        "route": "识别问题类型",
                        "resolve_order": "已确认订单",
                        "search": "已检索知识依据",
                        "business_query": "已核实业务数据",
                        "answer": "已完成回答",
                        "persist": "已保存",
                    }.get(node, "处理中"),
                }
    state = await graph.aget_state(config(thread_id))
    if state.interrupts:
        yield {"type": "paused", "orders": state.interrupts[0].value["orders"]}
        return
    async with sessions() as session:
        turn = await session.get(Turn, UUID(state.values["turn_id"]))
        if turn is None or turn.user_id != user_id:
            raise ValueError("Missing public answer")
        yield {"type": "support_answer", "answer": message_info(turn).model_dump(mode="json")}
    yield {"type": "done"}


async def evaluate(sessions, settings, model):
    async with sessions() as session:
        cases = (await session.scalars(select(EvaluationCase).order_by(EvaluationCase.id))).all()
    if not cases:
        raise ValueError("请先录入评估题")
    strategies, threshold_rows = [], []
    confusion = defaultdict(Counter)
    correct = 0
    for case in cases:
        predicted = classify(case.question)
        # 验收的是实际在线分类路径；真实模式与 workflow 使用相同结构化分类。
        if model is not None:
            from backend.app.modules.customer_service.workflow.graph import Classification

            result = await model.with_structured_output(Classification).ainvoke(
                "只分类客户问题：knowledge知识、order订单、logistics物流、refund退款、greeting问候。"
                f"客户问题：{case.question}"
            )
            predicted = result.intent
        confusion[case.intent][predicted] += 1
        correct += predicted == case.intent
    for strategy in ["keyword", "vector", "hybrid", "hybrid_rerank"]:
        hits = reciprocal = covered = 0
        retrieval_cases = [c for c in cases if c.intent == "knowledge" or c.expected_knowledge_id]
        for case in retrieval_cases:
            found = await retrieve(sessions, settings, case.question, strategy, model)
            ids = [item["knowledge_id"] for item in found]
            expected = str(case.expected_knowledge_id) if case.expected_knowledge_id else None
            rank = ids.index(expected) + 1 if expected in ids else 0
            hits += bool(rank)
            reciprocal += 1 / rank if rank else 0
            score = found[0]["score"] if found else 0
            covered += score >= settings.support_threshold
            if strategy == "hybrid_rerank":
                threshold_rows.append((score, expected is not None and bool(rank)))
        count = len(retrieval_cases)
        answerable = sum(c.expected_knowledge_id is not None for c in retrieval_cases)
        strategies.append(
            {
                "strategy": strategy,
                "recall": hits / (answerable or 1),
                "mrr": reciprocal / (answerable or 1),
                "coverage": covered / (count or 1),
                "count": count,
            }
        )
    thresholds = [i / 100 for i in range(10, 91, 5)]
    accuracies = [
        sum((score >= threshold) == valid for score, valid in threshold_rows)
        / (len(threshold_rows) or 1)
        for threshold in thresholds
    ]
    best = max(
        range(len(thresholds)),
        key=lambda i: (accuracies[i], -abs(thresholds[i] - settings.support_threshold)),
    )
    result = EvaluationResult(
        mode=settings.model_mode,
        dataset_size=len(cases),
        sources=sorted({c.source for c in cases}),
        strategies=strategies,
        classifier_accuracy=correct / len(cases),
        confusion={key: dict(value) for key, value in confusion.items()},
        recommended_threshold=thresholds[best],
        threshold_accuracy=accuracies[best],
        created_at=datetime.now(UTC),
    )
    async with sessions() as session:
        session.add(EvaluationRun(result=result.model_dump(mode="json")))
        await session.commit()
    return result


async def dashboard(session, settings):
    knowledge = (await session.scalars(select(Knowledge))).all()
    turns = (await session.scalars(select(Turn))).all()
    evaluation = await session.scalar(
        select(EvaluationRun).order_by(EvaluationRun.created_at.desc()).limit(1)
    )
    groups = defaultdict(list)
    for turn in turns:
        groups[turn.intent].append(turn)
    usage = []
    for intent, items in sorted(groups.items()):
        inputs = sum(item.usage.get("input_tokens", 0) for item in items)
        outputs = sum(item.usage.get("output_tokens", 0) for item in items)
        measured = sum(item.usage.get("measured_calls", 0) for item in items)
        cost = None
        if (
            measured
            and settings.input_price_per_million is not None
            and (settings.output_price_per_million is not None)
        ):
            cost = (
                inputs * settings.input_price_per_million
                + outputs * settings.output_price_per_million
            ) / 1_000_000
        usage.append(
            IntentUsage(
                intent=intent,
                calls=len(items),
                input_tokens=inputs,
                output_tokens=outputs,
                measured_calls=measured,
                estimated_cost_usd=cost,
            )
        )
    return Dashboard(
        knowledge_count=len(knowledge),
        indexed_count=sum(item.status == "indexed" for item in knowledge),
        pending_count=sum(item.review_status == "pending" for item in turns),
        handoff_count=sum(item.handoff for item in turns),
        conversations=len({item.thread_id for item in turns}),
        mode=settings.model_mode,
        threshold=settings.support_threshold,
        evaluation=EvaluationResult.model_validate(evaluation.result) if evaluation else None,
        usage=usage,
        topics=dict(Counter(item.intent for item in turns)),
    )
