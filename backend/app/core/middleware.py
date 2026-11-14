import logging
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class RequestBoundary:
    def __init__(self, app, settings):
        self.app, self.settings = app, settings

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request_id = str(uuid4())
        headers = Headers(scope=scope)
        if scope["method"] not in {"GET", "HEAD", "OPTIONS"}:
            origin = headers.get("origin")
            if (origin is not None and origin not in self.settings.allowed_origins) or headers.get(
                "sec-fetch-site"
            ) == "cross-site":
                response = JSONResponse({"detail": "请求来源不被允许"}, status_code=403)
                return await response(scope, receive, send)

        async def send_headers(message):
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(scope=message)
                response_headers["X-Request-ID"] = request_id
                response_headers["Cache-Control"] = "no-store"
                logger.info(
                    "request id=%s method=%s path=%s status=%s",
                    request_id,
                    scope["method"],
                    scope["path"],
                    message["status"],
                )
            await send(message)

        # 直接传递 ASGI receive/send，避免 BaseHTTPMiddleware 对流再包装和缓冲。
        await self.app(scope, receive, send_headers)
