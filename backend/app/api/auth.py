"""认证相关接口：登录、刷新、登出、当前用户档案、改密。

登录链路是本平台唯一的对外风险入口，因此所有分支（成功/失败/锁定/停用）
都会落一条登录日志，记录来源 IP、设备与失败原因。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_util import client_ip, ip_region, parse_ua
from app.core.config import settings
from app.core import token_store
from app.core.deps import CurrentUser, get_current_user
from app.core.orm import ensure_loaded
from app.core.security import (
    create_access_token, create_refresh_token, decode_token,
    hash_password, validate_password_strength, verify_password,
)
from app.db.session import get_db
from app.models import Tenant, User
from app.schemas import (
    ApiResponse, ChangePasswordIn, LoginIn, ProfileOut, RefreshIn, TokenOut, UserOut,
)
from app.services import permission as perm_svc
from app.services.audit import write_login_log

router = APIRouter(prefix="/auth", tags=["认证"])


async def _log_login(
    request: Request,
    *,
    username: str,
    tenant_id: int = 0,
    user_id: Optional[int] = None,
    status: int = 1,
    reason: Optional[str] = None,
    login_type: str = "login",
) -> None:
    """写登录日志：谁、几点、从哪个 IP、用什么设备、结果如何。"""
    ip = client_ip(request)
    ua = request.headers.get("user-agent")
    os_name, browser, device = parse_ua(ua)
    await write_login_log(
        tenant_id=tenant_id,
        user_id=user_id,
        username=username,
        login_type=login_type,
        status=status,
        fail_reason=reason,
        ip=ip,
        ip_region=ip_region(ip),
        user_agent=ua,
        os_name=os_name,
        browser=browser,
        device=device,
    )


@router.post("/login", response_model=ApiResponse[TokenOut], summary="登录")
async def login(body: LoginIn, request: Request, db: AsyncSession = Depends(get_db)):
    tenant = (await db.execute(
        select(Tenant).where(Tenant.code == body.tenant_code)
    )).scalar_one_or_none()
    if tenant is None or tenant.status != 1:
        await _log_login(request, username=body.username, status=0,
                         reason="租户不存在或已停用")
        raise HTTPException(400, "租户不存在或已停用")
    if tenant.expire_at and tenant.expire_at < datetime.now():
        await _log_login(request, username=body.username, tenant_id=tenant.id, status=0,
                         reason="租户已到期")
        raise HTTPException(400, "租户已到期，请联系平台管理员续期")

    user = (await db.execute(
        select(User).where(User.tenant_id == tenant.id, User.username == body.username)
    )).scalar_one_or_none()
    if user is None:
        await _log_login(request, username=body.username, tenant_id=tenant.id, status=0,
                         reason="用户名不存在")
        raise HTTPException(400, "用户名或密码错误")

    if user.locked_until and user.locked_until > datetime.now():
        left = int((user.locked_until - datetime.now()).total_seconds() // 60) + 1
        await _log_login(request, username=body.username, tenant_id=tenant.id,
                         user_id=user.id, status=0, reason=f"账号锁定中，剩余 {left} 分钟")
        raise HTTPException(423, f"账号已锁定，请 {left} 分钟后重试")
    if user.status != 1:
        await _log_login(request, username=body.username, tenant_id=tenant.id,
                         user_id=user.id, status=0, reason="账号已停用")
        raise HTTPException(403, "账号已停用，请联系管理员")

    if not verify_password(body.password, user.password_hash):
        user.login_fail_count += 1
        if user.login_fail_count >= settings.LOGIN_MAX_FAIL:
            user.locked_until = datetime.now() + timedelta(minutes=settings.LOGIN_LOCK_MINUTES)
            user.login_fail_count = 0
            await db.commit()
            await _log_login(request, username=body.username, tenant_id=tenant.id,
                             user_id=user.id, status=0,
                             reason=f"密码错误次数过多，锁定 {settings.LOGIN_LOCK_MINUTES} 分钟")
            raise HTTPException(423, f"密码错误次数过多，账号锁定 {settings.LOGIN_LOCK_MINUTES} 分钟")
        remain = settings.LOGIN_MAX_FAIL - user.login_fail_count
        await db.commit()
        await _log_login(request, username=body.username, tenant_id=tenant.id,
                         user_id=user.id, status=0, reason=f"密码错误，还可尝试 {remain} 次")
        raise HTTPException(400, f"用户名或密码错误，还可尝试 {remain} 次")

    user.login_fail_count = 0
    user.locked_until = None
    user.last_login_at = datetime.now()
    user.last_login_ip = request.client.host if request.client else None
    await db.commit()

    await _log_login(request, username=body.username, tenant_id=tenant.id,
                     user_id=user.id, status=1)

    # sid 标识一次登录会话：登出/改密时按 sid 一次性废掉该会话的 access+refresh
    sid = uuid.uuid4().hex
    return ApiResponse(data=TokenOut(
        access_token=create_access_token(str(user.id), tenant.id, sid=sid),
        refresh_token=create_refresh_token(str(user.id), tenant.id, sid=sid),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    ))


@router.post("/refresh", response_model=ApiResponse[TokenOut], summary="刷新令牌")
async def refresh_token(body: RefreshIn, request: Request, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token, "refresh")
    except JWTError:
        raise HTTPException(401, "刷新令牌无效或已过期")

    # 已登出（或改密）的会话不得再换发新令牌，否则登出形同虚设
    if await token_store.is_session_revoked(payload.get("sid")):
        raise HTTPException(401, "会话已失效，请重新登录")
    if await token_store.is_revoked(payload.get("jti")):
        raise HTTPException(401, "刷新令牌已使用或已失效，请重新登录")

    user_id, tenant_id = int(payload["sub"]), int(payload["tenant_id"])
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None or user.status != 1 or user.tenant_id != tenant_id:
        raise HTTPException(401, "账号状态异常，请重新登录")

    # 轮换：旧 refresh token 立即作废，防止被重放
    await token_store.revoke(payload)
    sid = payload.get("sid") or uuid.uuid4().hex
    return ApiResponse(data=TokenOut(
        access_token=create_access_token(str(user.id), tenant_id, sid=sid),
        refresh_token=create_refresh_token(str(user.id), tenant_id, sid=sid),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    ))


async def _revoke_request_token(request: Request) -> None:
    """撤销当前会话：access token 的 jti 与会话 sid 一并拉黑，refresh 也无法续命。"""
    raw = (request.headers.get("authorization") or "").strip()
    token = raw[7:].strip() if raw.lower().startswith("bearer ") else raw
    if not token:
        return
    try:
        payload = decode_token(token, "access")
    except JWTError:
        return  # 已过期/非法 token 无需处理
    await token_store.revoke(payload)
    await token_store.revoke_session(payload.get("sid"))


@router.post("/logout", response_model=ApiResponse[None], summary="登出")
async def logout(request: Request, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    await perm_svc.invalidate_user(user.id)
    await _revoke_request_token(request)
    await _log_login(request, username=user.username, tenant_id=user.tenant_id,
                     user_id=user.id, status=1, login_type="logout")
    return ApiResponse(msg="已退出登录")


@router.get("/profile", response_model=ApiResponse[ProfileOut], summary="当前用户档案（权限/菜单/角色）")
async def profile(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    ctx = await perm_svc.build_user_perm_payload(db, user)
    await ensure_loaded(db, user, ["roles"])
    tenant = (await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id)
    )).scalar_one()

    return ApiResponse(data=ProfileOut(
        user=UserOut.model_validate(user),
        tenant={"id": tenant.id, "code": tenant.code, "name": tenant.name},
        roles=ctx["roles"],
        permissions=ctx["permissions"],
        menus=perm_svc.build_menu_tree(ctx["menus"], only_visible=True),
        data_scope=ctx["data_scope"],
    ))


@router.put("/password", response_model=ApiResponse[None], summary="修改本人密码")
async def change_password(body: ChangePasswordIn, request: Request, user: CurrentUser,
                          db: AsyncSession = Depends(get_db)):
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(400, "原密码不正确")
    ok, msg = validate_password_strength(body.new_password)
    if not ok:
        raise HTTPException(400, msg)
    if body.old_password == body.new_password:
        raise HTTPException(400, "新密码不能与原密码相同")
    user.password_hash = hash_password(body.new_password)
    await db.commit()
    await perm_svc.invalidate_user(user.id)
    await _revoke_request_token(request)  # 旧 token 立即失效，需重新登录
    return ApiResponse(msg="密码修改成功")
