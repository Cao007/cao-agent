import asyncio

from alembic import context

from backend.app.core.config import Settings
from backend.app.db.session import Base, create_database
from backend.app.modules.auth import models as auth_models  # noqa: F401
from backend.app.modules.document_analysis import models as analysis_models  # noqa: F401
from backend.app.modules.threads import models as thread_models  # noqa: F401


def run(connection):
    context.configure(
        connection=connection,
        target_metadata=Base.metadata,
        # 官方 checkpointer 独立维护这些表，autogenerate 不能把它们当作待删除业务表。
        include_name=lambda name, kind, _: (
            kind != "table" or not (name == "checkpoints" or name.startswith("checkpoint_"))
        ),
    )
    with context.begin_transaction():
        context.run_migrations()


async def online():
    engine, _ = create_database(Settings().database_url)
    async with engine.connect() as connection:
        await connection.run_sync(run)
    await engine.dispose()


if context.is_offline_mode():
    context.configure(
        url=Settings().database_url.replace("postgresql://", "postgresql+psycopg://", 1),
        target_metadata=Base.metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(online())
