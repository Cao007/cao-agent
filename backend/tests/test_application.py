import asyncio
import json
import socket
from uuid import uuid4

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from backend.app.main import create_api
from backend.app.modules.document_analysis.schemas import Extraction
from backend.app.modules.threads.service import claim_thread


def events(response):
    assert response.status_code == 200, response.text
    return [
        json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")
    ]


def new_thread(client):
    response = client.post("/api/chat/threads", json={"title": "测试会话"})
    assert response.status_code == 201
    return response.json()["id"]


def test_authentication_and_csrf(client, login):
    response = client.get("/api/auth/me")
    assert response.json()["id"] == login["id"]
    assert (
        "HttpOnly"
        in client.post(
            "/api/auth/login",
            json={
                "username": login["username"],
                "password": "test-password-123",
            },
        ).headers["set-cookie"]
    )
    client.headers.pop("X-CSRF-Token")
    assert client.post("/api/chat/threads", json={}).status_code == 403
    client.headers["X-CSRF-Token"] = client.get("/api/auth/me").json()["csrf_token"]
    assert (
        client.post(
            "/api/chat/threads",
            json={},
            headers={
                "Origin": "https://untrusted.example",
            },
        ).status_code
        == 403
    )
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_chat_survives_application_restart(client, settings, login):
    thread_id = new_thread(client)
    output = events(
        client.post(f"/api/chat/threads/{thread_id}/messages", json={"message": "你好"})
    )
    assert output[-1]["type"] == "done"
    assert "演示模式" in "".join(e["content"] for e in output if e["type"] == "token")
    with TestClient(create_api(settings)) as restarted:
        restarted.cookies.update(client.cookies)
        restarted.headers["X-CSRF-Token"] = login["csrf_token"]
        detail = restarted.get(f"/api/chat/threads/{thread_id}").json()
        assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
        assert detail["status"] == "complete"
        output = events(
            restarted.post(
                f"/api/chat/threads/{thread_id}/messages",
                json={"message": "继续"},
            )
        )
        assert output[-1]["type"] == "done"
        assert len(restarted.get(f"/api/chat/threads/{thread_id}").json()["messages"]) == 4


def test_resource_ownership(client, settings, login):
    thread_id = new_thread(client)
    analysis_id = client.post("/api/analyses", json={"text": "私有文本"}).json()["id"]
    with TestClient(create_api(settings)) as other:
        user = other.post(
            "/api/auth/register",
            json={
                "username": f"other_{uuid4().hex}",
                "password": "test-password-123",
            },
        ).json()
        other.headers["X-CSRF-Token"] = user["csrf_token"]
        assert other.get("/api/chat/threads").json() == []
        assert other.get("/api/analyses").json() == []
        for path, body in [
            (f"/api/chat/threads/{thread_id}/messages", {"message": "覆盖"}),
            (f"/api/analyses/{analysis_id}/run", {}),
            (f"/api/analyses/{analysis_id}/resume", {"approved": True}),
        ]:
            assert other.post(path, json=body).status_code == 404
        assert other.get(f"/api/chat/threads/{thread_id}").status_code == 404
        assert other.get(f"/api/analyses/{analysis_id}").status_code == 404


@pytest.mark.parametrize("approved", [True, False])
def test_structured_extraction_interrupt_resume(client, settings, login, approved):
    analysis_id = client.post(
        "/api/analyses",
        json={
            "text": "团队本周完成原型，下周邀请五位用户试用。",
            "require_review": True,
        },
    ).json()["id"]
    output = events(client.post(f"/api/analyses/{analysis_id}/run"))
    assert output[-1]["type"] == "paused"
    Extraction.model_validate(output[-1]["review"])
    assert client.get(f"/api/analyses/{analysis_id}").json()["result"] is None
    with TestClient(create_api(settings)) as restarted:
        restarted.cookies.update(client.cookies)
        restarted.headers["X-CSRF-Token"] = login["csrf_token"]
        detail = restarted.get(f"/api/analyses/{analysis_id}").json()
        assert detail["status"] == "paused" and detail["review"]
        assert restarted.post(f"/api/analyses/{analysis_id}/run").status_code == 409
        output = events(
            restarted.post(
                f"/api/analyses/{analysis_id}/resume",
                json={"approved": approved},
            )
        )
        assert output[-1]["type"] == "done"
        detail = restarted.get(f"/api/analyses/{analysis_id}").json()
        assert detail["status"] == "complete"
        assert bool(detail["result"]) == approved
        assert (
            restarted.post(
                f"/api/analyses/{analysis_id}/resume",
                json={"approved": True},
            ).status_code
            == 409
        )


def test_same_thread_database_lock(client, login):
    thread_id = new_thread(client)
    lock = client.portal.call(claim_thread, client.app.state.engine, thread_id)
    try:
        assert (
            client.post(
                f"/api/chat/threads/{thread_id}/messages",
                json={"message": "并发请求"},
            ).status_code
            == 409
        )
    finally:
        client.portal.call(lock.close)
    assert (
        events(
            client.post(
                f"/api/chat/threads/{thread_id}/messages",
                json={"message": "释放后继续"},
            )
        )[-1]["type"]
        == "done"
    )


def test_validation_and_private_errors(client, login, monkeypatch):
    thread_id = new_thread(client)
    for message in ["   ", "a" * 16001]:
        assert (
            client.post(
                f"/api/chat/threads/{thread_id}/messages",
                json={"message": message},
            ).status_code
            == 422
        )
    assert client.post("/api/analyses", json={"text": "  "}).status_code == 422

    class BrokenGraph:
        async def astream(self, *args, **kwargs):
            yield AIMessage(content="部分输出"), {"langgraph_node": "respond"}
            raise RuntimeError("private-provider-secret")

    monkeypatch.setattr(client.app.state, "chat", BrokenGraph())
    response = client.post(
        f"/api/chat/threads/{thread_id}/messages",
        json={"message": "失败"},
    )
    assert events(response)[-1]["type"] == "error"
    assert "private-provider-secret" not in response.text
    # 错误后同一条记录的锁必须释放。
    lock = client.portal.call(claim_thread, client.app.state.engine, thread_id)
    client.portal.call(lock.close)


def test_provider_adapter_without_network(settings, monkeypatch):
    class FakeModel:
        async def ainvoke(self, messages):
            assert messages[-1].content == "输入"
            return AIMessage(content="供应商文本")

        def with_structured_output(self, schema):
            class Structured:
                async def ainvoke(self, messages):
                    return schema(title="结果", summary="摘要", key_points=[], action_items=[])

            return Structured()

    monkeypatch.setattr("backend.app.main.create_model", lambda _: FakeModel())
    with TestClient(create_api(settings)) as client:
        user = client.post(
            "/api/auth/register",
            json={
                "username": f"provider_{uuid4().hex}",
                "password": "test-password-123",
            },
        ).json()
        client.headers["X-CSRF-Token"] = user["csrf_token"]
        output = events(
            client.post(
                f"/api/chat/threads/{new_thread(client)}/messages",
                json={"message": "输入"},
            )
        )
        assert "".join(e["content"] for e in output if e["type"] == "token") == "供应商文本"
        analysis_id = client.post(
            "/api/analyses",
            json={"text": "输入", "require_review": False},
        ).json()["id"]
        output = events(client.post(f"/api/analyses/{analysis_id}/run"))
        assert next(e for e in output if e["type"] == "result")["result"]["title"] == "结果"


def test_http_disconnect_cancels_model_and_releases_lock(settings, monkeypatch):
    """使用真实 HTTP socket；TestClient 会缓冲 SSE，不能证明断连取消。"""

    async def check():
        started, cancelled = asyncio.Event(), asyncio.Event()
        disconnected = asyncio.Event()
        from backend.app.ai.streaming import DisconnectAwareResponse

        original_listener = DisconnectAwareResponse.listen_for_disconnect

        async def observe_disconnect(self, receive):
            await original_listener(self, receive)
            disconnected.set()

        monkeypatch.setattr(DisconnectAwareResponse, "listen_for_disconnect", observe_disconnect)

        class WaitingModel:
            def with_structured_output(self, schema):
                return self

            async def ainvoke(self, messages):
                started.set()
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    cancelled.set()
                    raise

        monkeypatch.setattr("backend.app.main.create_model", lambda _: WaitingModel())
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        ready = asyncio.Event()

        class Server(uvicorn.Server):
            async def startup(self, sockets=None):
                await super().startup(sockets)
                ready.set()

        server = Server(uvicorn.Config(create_api(settings), log_level="error"))
        task = asyncio.create_task(server.serve(sockets=[sock]))
        try:
            async with asyncio.timeout(10):
                await ready.wait()
                async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}") as client:
                    user = (
                        await client.post(
                            "/api/auth/register",
                            json={
                                "username": f"cancel_{uuid4().hex}",
                                "password": "test-password-123",
                            },
                        )
                    ).json()
                    client.headers["X-CSRF-Token"] = user["csrf_token"]
                    thread_id = (await client.post("/api/chat/threads", json={})).json()["id"]
                    async with client.stream(
                        "POST",
                        f"/api/chat/threads/{thread_id}/messages",
                        json={"message": "取消"},
                    ) as response:
                        assert response.status_code == 200
                        await started.wait()
                        assert (await anext(response.aiter_lines())).startswith("data: ")
                    await disconnected.wait()
                    await cancelled.wait()
                    while True:
                        detail = (await client.get(f"/api/chat/threads/{thread_id}")).json()
                        if detail["status"] == "cancelled":
                            break
                        await asyncio.sleep(0.01)
                    lock = await claim_thread(server.config.app.state.engine, thread_id)
                    await lock.close()
        finally:
            server.should_exit = True
            await task
            sock.close()

    asyncio.run(check())


def test_completed_checkpoint_can_reconcile_missing_business_result(client, login):
    analysis_id = client.post(
        "/api/analyses",
        json={"text": "需要恢复的原文", "require_review": False},
    ).json()["id"]
    # 模拟图已完成，但进程在正式结果写入业务表前退出。
    client.portal.call(
        client.app.state.analysis.ainvoke,
        {"source": "需要恢复的原文", "require_review": False},
        {"configurable": {"thread_id": analysis_id}},
    )
    assert client.get(f"/api/analyses/{analysis_id}").json()["result"] is None
    for _ in range(2):
        assert events(client.post(f"/api/analyses/{analysis_id}/run"))[-1]["type"] == "done"
        detail = client.get(f"/api/analyses/{analysis_id}").json()
        assert detail["result"]["summary"] == "需要恢复的原文"
        assert detail["status"] == "complete"
