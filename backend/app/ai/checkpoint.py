from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver


@asynccontextmanager
async def open_checkpointer(database_url: str):
    # setup 属于迁移入口，不能在每个应用 worker 启动时重复执行 DDL。
    async with AsyncPostgresSaver.from_conn_string(database_url) as saver:
        yield saver
