"""租户管理接口：仅平台超级管理员可操作。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_perm, require_platform_admin
from app.db.session import get_db
from app.models import Role, Tenant, User
from app.schemas import (
    ApiResponse, PageResult, TenantCreate, TenantOut, TenantUpdate,
)
from app.services import permission as perm_svc

router = APIRouter(prefix="/tenants", tags=["租户管理"],
                   dependencies=[Depends(require_platform_admin)])


@router.get("", response_model=ApiResponse[PageResult[TenantOut]], summary="租户列表",
            dependencies=[Depends(require_perm("system:tenant:list"))])
async def list_tenants(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str | None = None,
):
    stmt = select(Tenant)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(Tenant.name.like(like) | Tenant.code.like(like))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = list((await db.execute(
        stmt.order_by(Tenant.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars())
    return ApiResponse(data=PageResult(
        total=total, items=[TenantOut.model_validate(r) for r in rows]
    ))


@router.post("", response_model=ApiResponse[TenantOut], summary="新建租户",
             dependencies=[Depends(require_perm("system:tenant:create"))])
async def create_tenant(body: TenantCreate, db: AsyncSession = Depends(get_db)):
    if (await db.execute(select(Tenant).where(Tenant.code == body.code))).scalar_one_or_none():
        raise HTTPException(400, "租户编码已存在")
    tenant = Tenant(**body.model_dump())
    db.add(tenant)
    await db.flush()

    # 为每个新租户自动创建内置管理员角色，避免新租户无角色可用
    db.add(Role(
        tenant_id=tenant.id, code="tenant_admin", name="租户管理员",
        data_scope=1, is_system=True, sort=1, remark="内置角色，拥有本租户全部数据权限",
    ))
    await db.commit()
    return ApiResponse(data=TenantOut.model_validate(tenant), msg="创建成功")


@router.put("/{tenant_id}", response_model=ApiResponse[TenantOut], summary="编辑租户",
            dependencies=[Depends(require_perm("system:tenant:update"))])
async def update_tenant(tenant_id: int, body: TenantUpdate, db: AsyncSession = Depends(get_db)):
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(404, "租户不存在")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(tenant, field, value)
    await db.commit()
    return ApiResponse(data=TenantOut.model_validate(tenant), msg="更新成功")


@router.delete("/{tenant_id}", response_model=ApiResponse[None], summary="删除租户",
               dependencies=[Depends(require_perm("system:tenant:delete"))])
async def delete_tenant(tenant_id: int, db: AsyncSession = Depends(get_db)):
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(404, "租户不存在")
    user_count = (await db.execute(
        select(func.count()).select_from(User).where(User.tenant_id == tenant_id)
    )).scalar_one()
    if user_count:
        raise HTTPException(400, f"该租户下仍有 {user_count} 个用户，请先清理")
    await db.delete(tenant)
    await db.commit()
    await perm_svc.invalidate_tenant(tenant_id)
    return ApiResponse(msg="删除成功")
