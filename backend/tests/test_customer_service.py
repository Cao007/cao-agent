from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.main import create_api
from backend.app.modules.customer_service.models import Knowledge, Operator, Turn
from backend.app.modules.customer_service.seed import seed_knowledge, seed_orders
from backend.tests.test_application import events


def setup_operator(client, login):
    async def seed():
        async with client.app.state.sessions() as session:
            session.add(Operator(user_id=UUID(login["id"])))
            await seed_orders(session, UUID(login["id"]))
            await seed_knowledge(session, client.app.state.settings)
            await session.commit()

    client.portal.call(seed)


def thread(client):
    response = client.post("/api/support/threads", json={"title": "客服验收"})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def ask(client, thread_id, question):
    return events(
        client.post(f"/api/support/threads/{thread_id}/messages", json={"message": question})
    )


def answer(output):
    assert output[-1]["type"] == "done", output
    return next(item["answer"] for item in output if item["type"] == "support_answer")


def test_customer_citations_orders_refund_and_resume(client, settings, login):
    setup_operator(client, login)
    thread_id = thread(client)
    reply = answer(ask(client, thread_id, "保温杯怎么清洗"))
    assert "温水" in reply["content"]
    assert reply["citations"] and "[1]" in reply["content"]

    async def source():
        async with client.app.state.sessions() as session:
            return await session.get(Knowledge, UUID(reply["citations"][0]["knowledge_id"]))

    assert "温水" in client.portal.call(source).content
    policy = answer(ask(client, thread_id, "退货政策是什么"))
    assert policy["citations"] and "七天" in policy["content"]
    assert policy["tools"] == []
    reply = answer(ask(client, thread_id, "查订单1001物流到哪了"))
    assert reply["tools"] == ["query_order", "query_logistics"]
    assert "顺丰" in reply["content"]
    reply = answer(ask(client, thread_id, "它能退吗"))
    assert "1001" in reply["content"] and "符合演示" in reply["content"]
    assert reply["citations"][0]["title"] == "七天退货政策（演示）"
    another = thread(client)
    output = ask(client, another, "我买的东西能退吗")
    assert output[-1]["type"] == "paused"
    assert len(output[-1]["orders"]) == 3
    assert (
        client.post(
            f"/api/support/threads/{another}/messages", json={"message": "覆盖"}
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/support/threads/{another}/resume", json={"order_id": str(uuid4())}
        ).status_code
        == 422
    )
    order_id = output[-1]["orders"][1]["id"]
    with TestClient(create_api(settings)) as restarted:
        restarted.cookies.update(client.cookies)
        restarted.headers["X-CSRF-Token"] = login["csrf_token"]
        assert len(restarted.get(f"/api/support/threads/{another}").json()["orders_to_select"]) == 3
        reply = answer(
            events(
                restarted.post(
                    f"/api/support/threads/{another}/resume", json={"order_id": order_id}
                )
            )
        )
        assert "1002" in reply["content"] and "不符合" in reply["content"]
        assert (
            restarted.post(
                f"/api/support/threads/{another}/resume", json={"order_id": order_id}
            ).status_code
            == 409
        )
        detail = restarted.get(f"/api/support/threads/{another}").json()
        assert detail["status"] == "complete"
        assert detail["messages"][-1]["turn_id"] == reply["turn_id"]


def test_unknown_review_knowledge_flywheel(client, login):
    setup_operator(client, login)
    question = f"是否支持星际{uuid4().hex}协议"
    thread_id = thread(client)
    reply = answer(ask(client, thread_id, question))
    assert "无法确认" in reply["content"] and not reply["citations"]
    turn_id = reply["turn_id"]
    assert client.post(f"/api/support/turns/{turn_id}/handoff").json()["handoff"] is True
    assert (
        client.post(f"/api/support/turns/{turn_id}/feedback", json={"value": "down"}).json()[
            "feedback"
        ]
        == "down"
    )
    reviews = client.get("/api/support/admin/reviews").json()
    assert next(item for item in reviews if item["id"] == turn_id)["review_status"] == "pending"
    assert (
        client.post(
            f"/api/support/admin/reviews/{turn_id}", json={"action": "approve", "answer": ""}
        ).status_code
        == 422
    )
    correction = "该协议暂不支持，可使用普通配送服务。"
    response = client.post(
        f"/api/support/admin/reviews/{turn_id}",
        json={"action": "approve", "answer": correction},
    )
    assert response.status_code == 200, response.text
    assert response.json()["review_status"] == "approved"
    assert (
        client.post(f"/api/support/admin/reviews/{turn_id}", json={"action": "reject"}).status_code
        == 409
    )
    reply = answer(ask(client, thread_id, question))
    assert correction in reply["content"] and reply["citations"]
    knowledge_id = reply["citations"][0]["knowledge_id"]
    assert client.post(f"/api/support/admin/knowledge/{knowledge_id}/archive").status_code == 200
    reply = answer(ask(client, thread_id, question))
    assert "无法确认" in reply["content"]


def test_customer_ownership_operator_and_thread_lock(client, settings, login):
    setup_operator(client, login)
    thread_id = thread(client)
    output = ask(client, thread_id, "我买的东西能退吗")
    order_id = output[-1]["orders"][0]["id"]
    chat_id = client.post("/api/chat/threads", json={}).json()["id"]
    assert client.get(f"/api/support/threads/{chat_id}").status_code == 404
    with TestClient(create_api(settings)) as other:
        user = other.post(
            "/api/auth/register",
            json={"username": f"customer_{uuid4().hex}", "password": "test-password-123"},
        ).json()
        other.headers["X-CSRF-Token"] = user["csrf_token"]
        assert other.get("/api/support/profile").json()["is_operator"] is False
        assert other.get("/api/support/orders").json() == []
        assert other.get("/api/support/threads").json() == []
        assert other.get(f"/api/support/threads/{thread_id}").status_code == 404
        assert (
            other.post(
                f"/api/support/threads/{thread_id}/resume", json={"order_id": order_id}
            ).status_code
            == 404
        )
        for path in ["dashboard", "knowledge", "reviews", "evaluation-cases"]:
            assert other.get(f"/api/support/admin/{path}").status_code == 403
        assert (
            other.post(
                "/api/support/admin/knowledge", json={"title": "篡改", "content": "违规"}
            ).status_code
            == 403
        )
        own_thread = thread(other)
        own_orders = other.post("/api/support/demo-orders").json()
        assert len(own_orders) == 3 and own_orders[0]["id"] != order_id
        assert len(other.post("/api/support/demo-orders").json()) == 3
        ask(other, own_thread, "我买的东西能退吗")
        assert (
            other.post(
                f"/api/support/threads/{own_thread}/resume", json={"order_id": order_id}
            ).status_code
            == 422
        )
    reply = answer(
        events(client.post(f"/api/support/threads/{thread_id}/resume", json={"order_id": order_id}))
    )
    turn_id = reply["turn_id"]
    with TestClient(create_api(settings)) as other:
        other.cookies.update({})
        user = other.post(
            "/api/auth/register",
            json={"username": f"feedback_{uuid4().hex}", "password": "test-password-123"},
        ).json()
        other.headers["X-CSRF-Token"] = user["csrf_token"]
        for action, body in [("feedback", {"value": "down"}), ("handoff", {})]:
            assert (
                other.post(f"/api/support/turns/{turn_id}/{action}", json=body).status_code == 404
            )
    from backend.app.modules.threads.service import claim_thread

    lock = client.portal.call(claim_thread, client.app.state.engine, thread_id)
    try:
        assert (
            client.post(
                f"/api/support/threads/{thread_id}/messages", json={"message": "你好"}
            ).status_code
            == 409
        )
    finally:
        client.portal.call(lock.close)


def test_evaluation_metrics_are_computed_and_cost_unknown(client, login):
    setup_operator(client, login)
    measured_before = sum(
        item["measured_calls"]
        for item in client.get("/api/support/admin/dashboard").json()["usage"]
    )
    response = client.post("/api/support/admin/evaluate")
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["mode"] == "demo"
    assert result["dataset_size"] >= 9
    assert len(result["strategies"]) == 4
    for metric in result["strategies"]:
        assert all(0 <= metric[key] <= 1 for key in ["recall", "mrr", "coverage"])
    assert result["sources"] == ["本项目手写样例（非原始300题）"]
    assert result["classifier_accuracy"] == 1
    answer(ask(client, thread(client), "你好"))
    data = client.get("/api/support/admin/dashboard").json()
    assert data["evaluation"]["created_at"] == result["created_at"]
    assert data["topics"]["greeting"] >= 1
    assert all(item["estimated_cost_usd"] is None for item in data["usage"])
    assert sum(item["measured_calls"] for item in data["usage"]) == measured_before

    async def persisted():
        async with client.app.state.sessions() as session:
            return (
                await session.scalars(select(Turn).where(Turn.user_id == UUID(login["id"])))
            ).all()

    assert len(client.portal.call(persisted)) == 1
