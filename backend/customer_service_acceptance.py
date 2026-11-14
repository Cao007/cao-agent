"""对 Docker 提供的实际 HTTP 服务验收；账号和密码从环境读取。"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx


def run():
    url = os.environ.get("SUPPORT_URL", "http://127.0.0.1:8080")
    with httpx.Client(base_url=url, timeout=60) as client:
        login = client.post(
            "/api/auth/login",
            json={
                "username": os.environ["SUPPORT_USERNAME"],
                "password": os.environ["SUPPORT_PASSWORD"],
            },
        )
        login.raise_for_status()
        client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
        knowledge = client.get("/api/support/admin/knowledge").json()
        assert all(item["status"] == "indexed" for item in knowledge)
        # 浏览器审核已把这道未知题补入知识，验收同步更新其标注。
        correction = next(
            (item for item in knowledge if item["title"] == "你们能提供月球移民服务吗？"), None
        )
        if correction:
            for case in client.get("/api/support/admin/evaluation-cases").json():
                if case["question"] == "你们能提供月球移民服务吗":
                    updated = client.put(
                        f"/api/support/admin/evaluation-cases/{case['id']}",
                        json={
                            "question": case["question"],
                            "intent": "knowledge",
                            "expected_knowledge_id": correction["id"],
                            "source": "本项目手写样例（审核后更新，非原始300题）",
                        },
                    )
                    updated.raise_for_status()
            cases = client.get("/api/support/admin/evaluation-cases").json()
            if not any(case["question"] == "可办理木星采矿许可证吗" for case in cases):
                client.post(
                    "/api/support/admin/evaluation-cases",
                    json={
                        "question": "可办理木星采矿许可证吗",
                        "intent": "knowledge",
                        "expected_knowledge_id": None,
                        "source": "本项目手写样例（新增未知问题，非原始300题）",
                    },
                ).raise_for_status()

        created = client.post("/api/support/threads", json={"title": "Docker HTTP 验收"})
        created.raise_for_status()
        thread_id = created.json()["id"]

        def ask(question):
            response = client.post(
                f"/api/support/threads/{thread_id}/messages", json={"message": question}
            )
            response.raise_for_status()
            output = [
                json.loads(line[6:])
                for line in response.text.splitlines()
                if line.startswith("data: ")
            ]
            assert output[-1]["type"] == "done", output
            return next(item["answer"] for item in output if item["type"] == "support_answer")

        citation = ask("保温杯怎么清洗")
        assert "[1]" in citation["content"] and citation["citations"]
        logistics = ask("订单1001物流到哪了")
        assert logistics["tools"] == ["query_order", "query_logistics"]
        refund = ask("它能退吗")
        assert "1001" in refund["content"] and "符合演示" in refund["content"]
        if correction:
            repaired = ask("你们能提供月球移民服务吗？")
            assert correction["content"] in repaired["content"]
        unknown = ask(f"能否支持火星{uuid4().hex}服务")
        assert "无法确认" in unknown["content"] and not unknown["citations"]
        handoff = client.post(f"/api/support/turns/{unknown['turn_id']}/handoff")
        assert handoff.json()["handoff"]
        evaluation = client.post("/api/support/admin/evaluate")
        evaluation.raise_for_status()
        dashboard = client.get("/api/support/admin/dashboard").json()
        assert len(dashboard["evaluation"]["strategies"]) == 4

        with httpx.Client(base_url=url, timeout=60) as customer:
            response = customer.post(
                "/api/auth/register",
                json={
                    "username": f"acceptance_{uuid4().hex}",
                    "password": uuid4().hex,
                },
            )
            response.raise_for_status()
            customer.headers["X-CSRF-Token"] = response.json()["csrf_token"]
            assert customer.get("/api/support/admin/dashboard").status_code == 403
            assert customer.get(f"/api/support/threads/{thread_id}").status_code == 404
            assert (
                customer.post(
                    f"/api/support/turns/{unknown['turn_id']}/feedback", json={"value": "down"}
                ).status_code
                == 404
            )
        result = {
            "verified_at": datetime.now(UTC).isoformat(),
            "url": url,
            "mode": client.get("/api/health").json()["mode"],
            "checks": {
                "numbered_citations": True,
                "order_logistics": True,
                "refund_pronoun_resolution": True,
                "unknown_fallback_handoff": True,
                "reviewed_answer_retrievable": bool(correction),
                "operator_enforcement": True,
                "owner_isolation": True,
            },
            "evaluation": evaluation.json(),
        }
        Path("docs/CUSTOMER_SERVICE_VERIFICATION.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
