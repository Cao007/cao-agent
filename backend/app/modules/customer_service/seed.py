"""显式初始化样例知识和运营身份；不在 worker 启动时写入。"""

import argparse
import asyncio

from sqlalchemy import select

from backend.app.core.config import Settings
from backend.app.db.session import create_database
from backend.app.modules.auth.models import User
from backend.app.modules.customer_service.models import EvaluationCase, Knowledge, Operator, Order
from backend.app.modules.customer_service.retrieval import index_knowledge

SAMPLES = [
    (
        "七天退货政策（演示）",
        "refund",
        "退货退款政策：商品签收后七天内，未拆封且不影响二次销售可申请七天无理由退货。"
        "已拆封或签收超过七天不适用无理由退货。质量问题请联系客服核实。退款只在人工审核后处理。",
    ),
    (
        "配送说明（演示）",
        "shipping",
        "配送多久到？付款后48小时内发货，普通地区发货后3到5天送达。"
        "物流异常请提供订单编号联系客服。运费满99元包邮，不满99元收取8元。",
    ),
    (
        "商品保养（演示）",
        "product",
        "保温杯怎么清洗？请使用温水和中性洗涤剂清洗保温杯，避免钢丝球刮伤。"
        "不要放入微波炉，不建议使用洗碗机。",
    ),
    (
        "发票说明（演示）",
        "faq",
        "如何开发票？订单完成后可申请电子发票，提供抬头与税号，电子发票会在3个工作日内开具。",
    ),
]


async def seed_orders(session, user_id):
    # 唯一约束保证不生成重复订单；并发初始化用数据库锁串行化。
    await session.get(User, user_id, with_for_update=True)
    if await session.scalar(select(Order.id).where(Order.user_id == user_id).limit(1)):
        return
    for number, product, days, opened, logistics in [
        ("1001", "轻量保温杯", 3, False, "顺丰 · 已签收，包裹送达本人"),
        ("1002", "旅行收纳包", 12, False, "中通 · 已签收，包裹送达驿站"),
        ("1003", "便携咖啡杯", 2, True, "京东物流 · 已签收，包裹送达本人"),
    ]:
        session.add(
            Order(
                user_id=user_id,
                number=number,
                product=product,
                status="已签收",
                delivered_days=days,
                opened=opened,
                logistics=logistics,
            )
        )


async def seed_knowledge(session, settings):
    from sqlalchemy import text

    await session.execute(text("SELECT pg_advisory_xact_lock(712834001)"))
    for title, category, content in SAMPLES:
        item = await session.scalar(select(Knowledge).where(Knowledge.title == title))
        if item is None:
            item = Knowledge(title=title, category=category, content=content)
            await index_knowledge(item, settings)
            session.add(item)
            await session.flush()
            session.add(
                EvaluationCase(
                    question={
                        "refund": "退货退款政策是什么",
                        "shipping": "配送多久到",
                        "product": "保温杯怎么清洗",
                        "faq": "如何开发票",
                    }[category],
                    expected_knowledge_id=item.id,
                    intent="refund" if category == "refund" else "knowledge",
                    source="本项目手写样例（非原始300题）",
                )
            )
    if not await session.scalar(
        select(EvaluationCase.id).where(EvaluationCase.question == "你们能提供月球移民服务吗")
    ):
        for question, intent in [
            ("你们能提供月球移民服务吗", "knowledge"),
            ("查订单1001", "order"),
            ("订单1001物流到哪了", "logistics"),
            ("它能退吗", "refund"),
            ("你好", "greeting"),
        ]:
            session.add(
                EvaluationCase(
                    question=question, intent=intent, source="本项目手写样例（非原始300题）"
                )
            )


async def main(username):
    settings = Settings()
    engine, sessions = create_database(settings.database_url)
    try:
        async with sessions() as session:
            user = await session.scalar(select(User).where(User.username == username))
            if user is None:
                raise SystemExit("请先在应用注册该用户名，再运行初始化")
            if await session.get(Operator, user.id) is None:
                session.add(Operator(user_id=user.id))
            await seed_orders(session, user.id)
            await seed_knowledge(session, settings)
            await session.commit()
            print(f"已为 {username} 开通运营权限并初始化明确标记的样例数据")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--operator", required=True)
    asyncio.run(main(parser.parse_args().operator))
