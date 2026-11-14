import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, Response
from pwdlib import PasswordHash
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from backend.app.core.security import COOKIE_NAME, AuthenticatedUser, Session, token_hash
from backend.app.modules.auth.models import LoginSession, User
from backend.app.modules.auth.schemas import Credentials, CurrentUser

router = APIRouter(prefix="/api/auth", tags=["auth"])
password_hash = PasswordHash.recommended()
dummy_hash = password_hash.hash("unused-password-for-timing")


async def create_login(user: User, request: Request, response: Response, session: Session):
    settings = request.app.state.settings
    # 登录替换旧会话，令牌仅保存在 HttpOnly cookie，数据库只保存摘要。
    old_token = request.cookies.get(COOKIE_NAME)
    if old_token:
        await session.execute(
            delete(LoginSession).where(LoginSession.token_hash == token_hash(old_token))
        )
    await session.execute(delete(LoginSession).where(LoginSession.expires_at <= datetime.now(UTC)))
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    session.add(
        LoginSession(
            token_hash=token_hash(token),
            user_id=user.id,
            csrf_token=csrf,
            expires_at=datetime.now(UTC) + timedelta(hours=settings.session_hours),
        )
    )
    await session.commit()
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_hours * 3600,
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return CurrentUser(id=user.id, username=user.username, csrf_token=csrf)


@router.post("/register", response_model=CurrentUser, status_code=201)
async def register(body: Credentials, request: Request, response: Response, session: Session):
    if not request.app.state.settings.allow_registration:
        raise HTTPException(403, "注册已关闭")
    user = User(
        username=body.username.lower(),
        password_hash=await run_in_threadpool(password_hash.hash, body.password),
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, "用户名已存在") from None
    return await create_login(user, request, response, session)


@router.post("/login", response_model=CurrentUser)
async def login(body: Credentials, request: Request, response: Response, session: Session):
    user = await session.scalar(select(User).where(User.username == body.username.lower()))
    valid = await run_in_threadpool(
        password_hash.verify, body.password, user.password_hash if user else dummy_hash
    )
    if user is None or not valid:
        raise HTTPException(401, "用户名或密码错误")
    return await create_login(user, request, response, session)


@router.get("/me", response_model=CurrentUser)
async def me(user: AuthenticatedUser, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return user


@router.post("/logout", status_code=204)
async def logout(user: AuthenticatedUser, request: Request, response: Response, session: Session):
    await session.execute(
        delete(LoginSession).where(
            LoginSession.token_hash == token_hash(request.cookies[COOKIE_NAME])
        )
    )
    await session.commit()
    response.delete_cookie(COOKIE_NAME, path="/")
