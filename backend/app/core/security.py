import hashlib
import secrets
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_session
from backend.app.modules.auth.models import LoginSession, User
from backend.app.modules.auth.schemas import CurrentUser

Session = Annotated[AsyncSession, Depends(get_session)]
COOKIE_NAME = "cao_session"


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def current_user(request: Request, session: Session) -> CurrentUser:
    token = request.cookies.get(COOKIE_NAME)
    login = await session.get(LoginSession, token_hash(token)) if token else None
    if login is None or login.expires_at <= datetime.now(UTC):
        raise HTTPException(401, "请先登录")
    if request.method not in {"GET", "HEAD", "OPTIONS"} and not secrets.compare_digest(
        request.headers.get("X-CSRF-Token", ""), login.csrf_token
    ):
        raise HTTPException(403, "请求凭据无效，请刷新页面")
    user = await session.get(User, login.user_id)
    if user is None:
        raise HTTPException(401, "请先登录")
    return CurrentUser(id=user.id, username=user.username, csrf_token=login.csrf_token)


AuthenticatedUser = Annotated[CurrentUser, Depends(current_user)]
