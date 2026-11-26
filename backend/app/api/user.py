"""用户管理接口：全量数据范围过滤 + 功能权限校验。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import DataScope, CurrentUser, apply_data_scope, require_perm
from app.core.orm import ensure_loaded
from app.core.security import hash_password, validate_password_strength
from app.db.session import get_db
from app.models import Role, User
from app.schemas import (
    ApiResponse, PageResult, PasswordResetIn, UserCreate, UserOut, UserUpdate,
)
from app.services import permission as perm_svc

router = APIRouter(prefix="/users", tags=["用户管理"])


async def _get_user_in_scope(db: AsyncSession, user_id: int, tenant_id: int) -> User:
    user = (await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if user is None:
        raise HTTPException(404, "用户不存在或不属于当前租户")
    return user


async def _bind_roles(db: AsyncSession, user: User, role_ids: list[int], tenant_id: int):
    await ensure_loaded(db, user, ["roles"])
    if not role_ids:
        user.roles = []
        return
    roles = list((await db.execute(
        select(Role).where(Role.id.in_(role_ids), Role.tenant_id == tenant_id)
    )).scalars())
    if len(roles) != len(set(role_ids)):
        raise HTTPException(400, "包含无效角色或跨租户角色")
    user.roles = roles


@router.get("", response_model=ApiResponse[PageResult[UserOut]], summary="用户列表")
async def list_users(
    user: CurrentUser,
    scope: DataScope,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str | None = None,
    status: int | None = None,
    _=Depends(require_perm("system:user:list")),
):
    stmt = select(User).where(User.tenant_id == user.tenant_id)
    stmt = apply_data_scope(stmt, User, scope)

    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(User.username.like(like), User.nickname.like(like),
                              User.phone.like(like)))
    if status is not None:
        stmt = stmt.where(User.status == status)

    total = (await db.execute(
        select(func.count()).select_from(stmt.subquery())
    )).scalar_one()

    rows = list((await db.execute(
        stmt.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars())

    return ApiResponse(data=PageResult(
        total=total, items=[UserOut.model_validate(r) for r in rows]
    ))


@router.post("", response_model=ApiResponse[UserOut], summary="新建用户",
             dependencies=[Depends(require_perm("system:user:create"))])
async def create_user(body: UserCreate, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    exists = (await db.execute(
        select(User).where(User.tenant_id == user.tenant_id, User.username == body.username)
    )).scalar_one_or_none()
    if exists:
        raise HTTPException(400, "该租户下用户名已存在")

    ok, msg = validate_password_strength(body.password)
    if not ok:
        raise HTTPException(400, msg)

    new_user = User(
        tenant_id=user.tenant_id,
        username=body.username,
        nickname=body.nickname or body.username,
        password_hash=hash_password(body.password),
        email=str(body.email) if body.email else None,
        phone=body.phone,
        dept_id=body.dept_id,
        status=body.status,
    )
    db.add(new_user)
    await db.flush()
    await _bind_roles(db, new_user, body.role_ids, user.tenant_id)
    await db.commit()
    return ApiResponse(data=UserOut.model_validate(new_user), msg="创建成功")


@router.put("/{user_id}", response_model=ApiResponse[UserOut], summary="编辑用户",
            dependencies=[Depends(require_perm("system:user:update"))])
async def update_user(user_id: int, body: UserUpdate, user: CurrentUser,
                      db: AsyncSession = Depends(get_db)):
    target = await _get_user_in_scope(db, user_id, user.tenant_id)
    if target.is_superuser and not user.is_superuser:
        raise HTTPException(403, "无权修改超级管理员")

    for field in ("nickname", "phone", "dept_id", "status"):
        value = getattr(body, field)
        if value is not None:
            setattr(target, field, value)
    if body.email is not None:
        target.email = str(body.email)
    if body.role_ids is not None:
        await _bind_roles(db, target, body.role_ids, user.tenant_id)
    else:
        await ensure_loaded(db, target, ["roles"])

    await db.commit()
    await perm_svc.invalidate_user(target.id)
    return ApiResponse(data=UserOut.model_validate(target), msg="更新成功")


@router.delete("/{user_id}", response_model=ApiResponse[None], summary="删除用户",
               dependencies=[Depends(require_perm("system:user:delete"))])
async def delete_user(user_id: int, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    if user_id == user.id:
        raise HTTPException(400, "不能删除当前登录账号")
    target = await _get_user_in_scope(db, user_id, user.tenant_id)
    if target.is_superuser:
        raise HTTPException(403, "超级管理员不可删除")
    await db.delete(target)
    await db.commit()
    await perm_svc.invalidate_user(user_id)
    return ApiResponse(msg="删除成功")


@router.put("/{user_id}/password", response_model=ApiResponse[None], summary="重置密码",
            dependencies=[Depends(require_perm("system:user:resetPwd"))])
async def reset_password(user_id: int, body: PasswordResetIn, user: CurrentUser,
                         db: AsyncSession = Depends(get_db)):
    target = await _get_user_in_scope(db, user_id, user.tenant_id)
    ok, msg = validate_password_strength(body.new_password)
    if not ok:
        raise HTTPException(400, msg)
    target.password_hash = hash_password(body.new_password)
    target.login_fail_count = 0
    target.locked_until = None
    await db.commit()
    await perm_svc.invalidate_user(target.id)
    return ApiResponse(msg="密码已重置")
