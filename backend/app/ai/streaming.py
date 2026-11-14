import asyncio
import json
import logging
from uuid import UUID, uuid4

import anyio
from fastapi import Request
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from backend.app.modules.threads.service import set_status

logger = logging.getLogger(__name__)


class DisconnectAwareResponse(StreamingResponse):
    async def __call__(self, scope, receive, send):
        # ASGI 2.4 的默认实现靠 send 发现断连；模型等待期间没有 send，
        # 因而显式监听 http.disconnect，保证 AbortController 能取消上游调用。
        # LangGraph 用 asyncio 子任务；一次 cancel 后等待其退出，避免 AnyIO
        # level cancellation 在 graph 清理阶段反复打断 checkpoint 与子任务取消。
        stream_task = asyncio.create_task(self.stream_response(send))
        disconnect_task = asyncio.create_task(self.listen_for_disconnect(receive))
        try:
            done, _ = await asyncio.wait(
                {stream_task, disconnect_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in done:
                task.result()
        finally:
            stream_task.cancel()
            disconnect_task.cancel()
            with anyio.CancelScope(shield=True):
                await asyncio.gather(stream_task, disconnect_task, return_exceptions=True)
                if self.background is not None:
                    await self.background()


def event(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def stream_response(request: Request, thread_id: UUID, lock, execute):
    """只传领域事件；内部 graph state、提示词和供应商异常留在后端。"""
    run_id = str(uuid4())
    sessions = request.app.state.sessions

    async def close_lock():
        # StreamingResponse 取消时在 AnyIO cancel scope 内，清理必须 shield。
        with anyio.CancelScope(shield=True):
            await lock.close()

    async def stream():
        terminal = False
        try:
            await set_status(sessions, thread_id, "running")
            yield event({"type": "start", "run_id": run_id})
            async for output in execute():
                if output["type"] in {"done", "paused"}:
                    terminal = True
                    await set_status(
                        sessions, thread_id, "paused" if output["type"] == "paused" else "complete"
                    )
                yield event(output)
            if not terminal:
                raise RuntimeError("Workflow did not produce a terminal result")
        except asyncio.CancelledError:
            with anyio.CancelScope(shield=True):
                await set_status(sessions, thread_id, "cancelled")
            raise
        except Exception:
            logger.exception("workflow_failed run_id=%s thread_id=%s", run_id, thread_id)
            await set_status(sessions, thread_id, "error")
            yield event(
                {
                    "type": "error",
                    "message": "运行失败，请稍后重试或检查模型配置。",
                    "run_id": run_id,
                }
            )
        finally:
            await close_lock()

    return DisconnectAwareResponse(
        stream(),
        media_type="text/event-stream",
        background=BackgroundTask(close_lock),
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
