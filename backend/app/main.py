import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from backend.app.ai.checkpoint import open_checkpointer
from backend.app.ai.model import create_model
from backend.app.core.config import Settings
from backend.app.core.logging import configure_logging
from backend.app.core.middleware import RequestBoundary
from backend.app.db.session import create_database
from backend.app.modules.auth.router import router as auth_router
from backend.app.modules.chat.router import router as chat_router
from backend.app.modules.chat.workflow.graph import create_graph as create_chat
from backend.app.modules.document_analysis.router import router as analysis_router
from backend.app.modules.document_analysis.workflow.graph import create_graph as create_analysis

logger = logging.getLogger(__name__)


def create_api(settings: Settings | None = None):
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(api: FastAPI):
        configure_logging()
        engine, sessions = create_database(settings.database_url)
        api.state.engine, api.state.sessions = engine, sessions
        try:
            async with open_checkpointer(settings.database_url) as saver:
                model = create_model(settings)
                api.state.chat = create_chat(model, saver)
                api.state.analysis = create_analysis(model, saver)
                yield
        finally:
            await engine.dispose()

    api = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    api.state.settings = settings
    api.add_middleware(RequestBoundary, settings=settings)
    api.include_router(auth_router)
    api.include_router(chat_router)
    api.include_router(analysis_router)

    @api.exception_handler(Exception)
    async def unexpected_error(request: Request, exception: Exception):
        logger.error("request_failed path=%s", request.url.path, exc_info=exception)
        return JSONResponse({"detail": "服务异常，请稍后重试"}, status_code=500)

    @api.get("/api/health")
    async def health(request: Request):
        async with request.app.state.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return {"status": "ok", "mode": settings.model_mode, "model": settings.model_name}

    return api


app = create_api()
