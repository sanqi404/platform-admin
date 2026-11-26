"""FastAPI 依赖：当前用户、权限校验、数据范围、租户隔离。"""
from __future__ import annotations

from typing import Annotated, Callable, Optional

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import token_store
from app.core.security import decode_token
from app.db.session import get_db
from app.models import Tenant, User
from app.services import permission as perm_svc

bearer = HTTPBearer(auto_error=False)

CRED_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="登录状态已失效，请重新登录",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    cred: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if cred is None:
        raise CRED_EXC
    try:
        payload = decode_token(cred.credentials, "access")
    except JWTError:
        raise CRED_EXC

    # 已登出/改密的 token 立即失效（黑名单存于缓存后端；jti 单令牌 + sid 整会话）
    if await token_store.is_revoked(payload.get("jti")):
        raise CRED_EXC
    if await token_store.is_session_revoked(payload.get("sid")):
        raise CRED_EXC

    user_id = int(payload.get("sub", 0))
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None or user.status != 1:
        raise CRED_EXC
    if user.tenant_id != int(payload.get("tenant_id", -1)):
        raise CRED_EXC  # token 与租户不匹配，防伪造跨租户
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_tenant(
    user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> Tenant:
    tenant = (await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id)
    )).scalar_one_or_none()
    if tenant is None or tenant.status != 1:
        raise HTTPException(status_code=403, detail="租户已停用，请联系平台管理员")
    return tenant


CurrentTenant = Annotated[Tenant, Depends(get_current_tenant)]


async def get_perm_context(
    user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> dict:
    return await perm_svc.build_user_perm_payload(db, user)


PermContext = Annotated[dict, Depends(get_perm_context)]


# --------------------------------------------------------------------------- #
# 权限校验工厂
# --------------------------------------------------------------------------- #
def require_perm(*codes: str, mode: str = "any") -> Callable:
    """接口级权限校验。

    用法：
        @router.post("/users", dependencies=[Depends(require_perm("system:user:create"))])
    """
    async def _checker(ctx: PermContext) -> None:
        if not perm_svc.has_permission(ctx["permissions"], codes, mode):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"无操作权限，需要：{' 或 '.join(codes)}",
            )

    return _checker


def require_role(*role_codes: str) -> Callable:
    async def _checker(ctx: PermContext) -> None:
        if not set(ctx["roles"]) & set(role_codes):
            raise HTTPException(status_code=403, detail="角色不符，无访问权限")

    return _checker


async def require_platform_admin(ctx: PermContext) -> None:
    """平台级操作（如租户管理）仅超管可执行。"""
    if perm_svc.SUPER_PERM not in ctx["permissions"]:
        raise HTTPException(status_code=403, detail="仅平台管理员可执行该操作")


async def get_data_scope(
    user: CurrentUser,
    ctx: PermContext,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """返回 {"scope": int, "dept_ids": list[int] | None, "user_id": int}。
    dept_ids 为 None 表示不限制部门。
    """
    dept_ids = await perm_svc.resolve_dept_ids(db, user, ctx)
    return {"scope": ctx["data_scope"], "dept_ids": dept_ids, "user_id": user.id}


DataScope = Annotated[dict, Depends(get_data_scope)]


def apply_data_scope(stmt, model, scope: dict, dept_field: str = "dept_id",
                     user_field: str = "id"):
    """把数据范围条件拼进任意 select 语句。

    - 全部数据：不加条件
    - 仅本人：按 user_field 过滤
    - 部门/自定义：按 dept_field in (...) 过滤
    """
    if scope["dept_ids"] is None:
        return stmt
    if scope["scope"] == 4:
        return stmt.where(getattr(model, user_field) == scope["user_id"])
    ids = scope["dept_ids"] or [-1]
    return stmt.where(getattr(model, dept_field).in_(ids))
