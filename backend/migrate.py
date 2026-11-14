import asyncio

from alembic import command
from alembic.config import Config

from backend.app.ai.checkpoint import open_checkpointer
from backend.app.core.config import Settings


async def setup_checkpoints():
    async with open_checkpointer(Settings().database_url) as saver:
        await saver.setup()


if __name__ == "__main__":
    command.upgrade(Config("alembic.ini"), "head")
    asyncio.run(setup_checkpoints())
