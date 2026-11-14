from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from backend.app.modules.threads.models import Thread


async def owned_thread(session: AsyncSession, thread_id: UUID, user_id: UUID, module: str):
    thread = await session.scalar(
        select(Thread).where(
            Thread.id == thread_id,
            Thread.user_id == user_id,
            Thread.module == module,
        )
    )
    if thread is None:
        raise HTTPException(404, "记录不存在")
    return thread


async def claim_thread(engine: AsyncEngine, thread_id: UUID):
    """事务级 advisory lock 跨 worker 有效；断连、进程退出均由 PostgreSQL 释放。"""
    connection = await engine.connect()
    try:
        await connection.begin()
        acquired = await connection.scalar(
            text("SELECT pg_try_advisory_xact_lock(hashtextextended(:id, 0))"),
            {"id": str(thread_id)},
        )
        if not acquired:
            raise HTTPException(409, "此记录正在运行，请稍后重试")
        return connection
    except BaseException:
        await connection.close()
        raise


async def set_status(sessions, thread_id: UUID, status: str):
    async with sessions() as session:
        await session.execute(update(Thread).where(Thread.id == thread_id).values(status=status))
        await session.commit()
