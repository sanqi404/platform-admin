"""角色管理接口：含功能权限与菜单权限的授权。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.orm import ensure_loaded
from app.core.deps import CurrentUser, require_perm
from app.db.session import get_db
from app.models import Menu, Permission, Role
from app.schemas import (
    ApiResponse, RoleCreate, RoleGrantIn, RoleOut, RoleUpdate,
)
from app.services import permission as perm_svc

router = APIRouter(prefix="/roles", tags=["角色管理"])


async def _get_role(db: AsyncSession, role_id: int, tenant_id: int) -> Role:
    role = (await db.execute(
        select(Role).where(Role.id == role_id, Role.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if role is None:
        raise HTTPException(404, "角色不存在或不属于当前租户")
    return role


async def _tenant_menus(db: AsyncSession) -> list[Menu]:
    return list((await db.execute(
        select(Menu).where(Menu.status == 1).order_by(Menu.sort)
    )).scalars())


def _with_ancestors(menus: list[Menu], all_menus: list[Menu]) -> list[Menu]:
    """补齐上级目录：只授子菜单时若缺父节点，侧边栏不会渲染该分支。"""
    by_id = {m.id: m for m in all_menus}
    keep: dict[int, Menu] = {m.id: m for m in menus}
    for m in list(menus):
        parent = m.parent_id
        while parent and parent in by_id and parent not in keep:
            keep[parent] = by_id[parent]
            parent = by_id[parent].parent_id
    return sorted(keep.values(), key=lambda m: (m.sort, m.id))


def _default_base_menus(all_menus: list[Menu]) -> list[Menu]:
    """新建角色的默认可见菜单：一级目录 + 不绑定权限点的页面，保证角色不是空壳。"""
    picked = [m for m in all_menus if m.type == "dir" and m.parent_id == 0]
    picked += [m for m in all_menus if m.type == "menu" and not m.perm_code]
    return sorted({m.id: m for m in picked}.values(), key=lambda m: (m.sort, m.id))


@router.get("", response_model=ApiResponse[list[RoleOut]], summary="角色列表",
            dependencies=[Depends(require_perm("system:role:list"))])
async def list_roles(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    rows = list((await db.execute(
        select(Role).where(Role.tenant_id == user.tenant_id).order_by(Role.sort, Role.id)
    )).scalars())
    return ApiResponse(data=[RoleOut.model_validate(r) for r in rows])


@router.post("", response_model=ApiResponse[RoleOut], summary="新建角色",
             dependencies=[Depends(require_perm("system:role:create"))])
async def create_role(body: RoleCreate, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    if body.data_scope not in (1, 2, 3, 4, 5):
        raise HTTPException(400, "数据范围取值必须为 1-5")
    exists = (await db.execute(
        select(Role).where(Role.tenant_id == user.tenant_id, Role.code == body.code)
    )).scalar_one_or_none()
    if exists:
        raise HTTPException(400, "角色标识已存在")

    role = Role(
        tenant_id=user.tenant_id,
        code=body.code,
        name=body.name,
        data_scope=body.data_scope,
        custom_dept_ids=body.custom_dept_ids,
        status=body.status,
        sort=body.sort,
        remark=body.remark,
    )
    db.add(role)
    await db.commit()
    await perm_svc.invalidate_tenant(user.tenant_id)
    return ApiResponse(data=RoleOut.model_validate(role), msg="创建成功")


@router.put("/{role_id}", response_model=ApiResponse[RoleOut], summary="编辑角色",
            dependencies=[Depends(require_perm("system:role:update"))])
async def update_role(role_id: int, body: RoleUpdate, user: CurrentUser,
                      db: AsyncSession = Depends(get_db)):
    role = await _get_role(db, role_id, user.tenant_id)
    if role.is_system and body.status == 0:
        raise HTTPException(400, "内置角色不可停用")
    for field in ("name", "data_scope", "custom_dept_ids", "status", "sort", "remark"):
        value = getattr(body, field)
        if value is not None:
            setattr(role, field, value)
    await db.commit()
    await perm_svc.invalidate_tenant(user.tenant_id)
    return ApiResponse(data=RoleOut.model_validate(role), msg="更新成功")


@router.delete("/{role_id}", response_model=ApiResponse[None], summary="删除角色",
               dependencies=[Depends(require_perm("system:role:delete"))])
async def delete_role(role_id: int, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    role = await _get_role(db, role_id, user.tenant_id)
    if role.is_system:
        raise HTTPException(400, "内置角色不可删除")
    if role.users:
        raise HTTPException(400, f"该角色下仍有 {len(role.users)} 个用户，请先解绑")
    await db.delete(role)
    await db.commit()
    await perm_svc.invalidate_tenant(user.tenant_id)
    return ApiResponse(msg="删除成功")


@router.get("/{role_id}/grants", response_model=ApiResponse[dict], summary="查询角色授权",
            dependencies=[Depends(require_perm("system:role:list"))])
async def get_grants(role_id: int, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    role = await _get_role(db, role_id, user.tenant_id)
    return ApiResponse(data={
        "permission_ids": [p.id for p in role.permissions],
        "menu_ids": [m.id for m in role.menus],
        "data_scope": role.data_scope,
        "custom_dept_ids": role.custom_dept_ids or [],
        "is_all_perm": bool(role.is_all_perm),
    })


@router.put("/{role_id}/grants", response_model=ApiResponse[None], summary="保存角色授权",
            dependencies=[Depends(require_perm("system:role:grant"))])
async def grant(role_id: int, body: RoleGrantIn, user: CurrentUser,
                db: AsyncSession = Depends(get_db)):
    role = await _get_role(db, role_id, user.tenant_id)
    await ensure_loaded(db, role, ["permissions", "menus"])

    if body.is_all_perm:
        role.is_all_perm = True
        role.permissions = []
        role.menus = []
        role.data_scope = 1
        await db.commit()
        await perm_svc.invalidate_tenant(user.tenant_id)
        return ApiResponse(msg="已授予全量权限，即刻生效")

    if body.data_scope is not None and body.data_scope not in (1, 2, 3, 4, 5):
        raise HTTPException(400, "数据范围取值必须为 1-5")

    perms = list((await db.execute(
        select(Permission).where(Permission.id.in_(body.permission_ids))
    )).scalars()) if body.permission_ids else []
    menus = list((await db.execute(
        select(Menu).where(Menu.id.in_(body.menu_ids))
    )).scalars()) if body.menu_ids else []

    if len(perms) != len(set(body.permission_ids)):
        raise HTTPException(400, "包含无效权限点")
    if len(menus) != len(set(body.menu_ids)):
        raise HTTPException(400, "包含无效菜单")

    # 权限点与菜单双向推导：给了权限点就补上对应菜单，反之补上权限点，杜绝"有权限却看不到入口"
    all_menus = await _tenant_menus(db)
    all_perms = list((await db.execute(select(Permission))).scalars())
    menu_by_code = {m.perm_code: m for m in all_menus if m.perm_code}
    perm_by_code = {p.code: p for p in all_perms}
    have_perm = {p.code for p in perms}
    have_menu = {m.perm_code for m in menus if m.perm_code}
    for code in sorted(have_perm - have_menu):
        extra = menu_by_code.get(code)
        if extra is not None:
            menus.append(extra)
    for code in sorted(have_menu - have_perm):
        extra_perm = perm_by_code.get(code)
        if extra_perm is not None:
            perms.append(extra_perm)

    role.is_all_perm = False
    role.permissions = list({p.id: p for p in perms}.values())
    role.menus = _with_ancestors(list({m.id: m for m in menus}.values()), all_menus)
    if body.data_scope is not None:
        role.data_scope = body.data_scope
    await db.commit()
    await perm_svc.invalidate_tenant(user.tenant_id)
    return ApiResponse(msg="授权已生效")
