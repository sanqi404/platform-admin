"""日志审计接口：登录日志、操作日志的查询与清理。

隔离原则与业务接口一致：一律按当前登录人的 tenant_id 过滤，
租户之间互相不可见；不做跨租户「全局日志」入口，避免越权。
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, require_perm
from app.db.session import get_db
from app.models import LoginLog, OperationLog
from app.schemas import (
    ApiResponse, LoginLogOut, LogCleanIn, OperationLogOut, PageResult,
)

router = APIRouter(prefix="/logs", tags=["日志审计"])


# --------------------------------------------------------------------------- #
# 登录日志
# --------------------------------------------------------------------------- #
@router.get("/login", response_model=ApiResponse[PageResult[LoginLogOut]],
            summary="登录日志列表")
async def list_login_logs(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    username: str | None = None,
    status: int | None = Query(None, description="1成功 0失败"),
    login_type: str | None = None,
    ip: str | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    _=Depends(require_perm("system:loginlog:list")),
):
    stmt = select(LoginLog).where(LoginLog.tenant_id == user.tenant_id)
    if username:
        stmt = stmt.where(LoginLog.username.like(f"%{username}%"))
    if status is not None:
        stmt = stmt.where(LoginLog.status == status)
    if login_type:
        stmt = stmt.where(LoginLog.login_type == login_type)
    if ip:
        stmt = stmt.where(LoginLog.ip.like(f"%{ip}%"))
    if start_at:
        stmt = stmt.where(LoginLog.login_at >= start_at)
    if end_at:
        stmt = stmt.where(LoginLog.login_at <= end_at)

    total = (await db.execute(
        select(func.count()).select_from(stmt.subquery())
    )).scalar_one()
    rows = list((await db.execute(
        stmt.order_by(LoginLog.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars())

    return ApiResponse(data=PageResult(
        total=total, items=[LoginLogOut.model_validate(r) for r in rows]
    ))


# --------------------------------------------------------------------------- #
# 操作日志
# --------------------------------------------------------------------------- #
@router.get("/operation", response_model=ApiResponse[PageResult[OperationLogOut]],
            summary="操作日志列表")
async def list_operation_logs(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    username: str | None = None,
    module: str | None = None,
    action: str | None = None,
    success: bool | None = None,
    keyword: str | None = Query(None, description="模糊匹配路径 / 操作对象 / 动作描述"),
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    _=Depends(require_perm("system:operlog:list")),
):
    stmt = select(OperationLog).where(OperationLog.tenant_id == user.tenant_id)
    if username:
        stmt = stmt.where(OperationLog.username.like(f"%{username}%"))
    if module:
        stmt = stmt.where(OperationLog.module == module)
    if action:
        stmt = stmt.where(OperationLog.action == action)
    if success is not None:
        stmt = stmt.where(OperationLog.success.is_(success))
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(
            OperationLog.path.like(like),
            OperationLog.target.like(like),
            OperationLog.action_label.like(like),
        ))
    if start_at:
        stmt = stmt.where(OperationLog.created_at >= start_at)
    if end_at:
        stmt = stmt.where(OperationLog.created_at <= end_at)

    total = (await db.execute(
        select(func.count()).select_from(stmt.subquery())
    )).scalar_one()
    rows = list((await db.execute(
        stmt.order_by(OperationLog.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars())

    return ApiResponse(data=PageResult(
        total=total, items=[OperationLogOut.model_validate(r) for r in rows]
    ))


@router.get("/operation/{log_id}", response_model=ApiResponse[OperationLogOut],
            summary="操作日志详情（含完整请求参数）")
async def get_operation_log(
    log_id: int,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_perm("system:operlog:list")),
):
    row = (await db.execute(
        select(OperationLog).where(OperationLog.id == log_id,
                                   OperationLog.tenant_id == user.tenant_id)
    )).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "日志不存在")
    return ApiResponse(data=OperationLogOut.model_validate(row))


# --------------------------------------------------------------------------- #
# 清理（保留清理动作本身的操作日志，属于正常审计行为）
# --------------------------------------------------------------------------- #
@router.delete("/login/{log_id}", response_model=ApiResponse[None], summary="删除单条登录日志",
               dependencies=[Depends(require_perm("system:loginlog:delete"))])
async def delete_login_log(log_id: int, user: CurrentUser,
                           db: AsyncSession = Depends(get_db)):
    row = (await db.execute(
        select(LoginLog).where(LoginLog.id == log_id,
                               LoginLog.tenant_id == user.tenant_id)
    )).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "日志不存在")
    await db.delete(row)
    await db.commit()
    return ApiResponse(msg="已删除")


@router.delete("/operation/{log_id}", response_model=ApiResponse[None], summary="删除单条操作日志",
               dependencies=[Depends(require_perm("system:operlog:delete"))])
async def delete_operation_log(log_id: int, user: CurrentUser,
                               db: AsyncSession = Depends(get_db)):
    row = (await db.execute(
        select(OperationLog).where(OperationLog.id == log_id,
                                   OperationLog.tenant_id == user.tenant_id)
    )).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "日志不存在")
    await db.delete(row)
    await db.commit()
    return ApiResponse(msg="已删除")


@router.post("/login/clean", response_model=ApiResponse[dict], summary="清理指定时间之前的登录日志")
async def clean_login_logs(body: LogCleanIn, user: CurrentUser,
                           db: AsyncSession = Depends(get_db),
                           _=Depends(require_perm("system:loginlog:delete"))):
    result = await db.execute(
        delete(LoginLog).where(LoginLog.tenant_id == user.tenant_id,
                               LoginLog.login_at < body.before)
    )
    await db.commit()
    return ApiResponse(data={"deleted": result.rowcount or 0})


@router.post("/operation/clean", response_model=ApiResponse[dict], summary="清理指定时间之前的操作日志")
async def clean_operation_logs(body: LogCleanIn, user: CurrentUser,
                               db: AsyncSession = Depends(get_db),
                               _=Depends(require_perm("system:operlog:delete"))):
    result = await db.execute(
        delete(OperationLog).where(OperationLog.tenant_id == user.tenant_id,
                                   OperationLog.created_at < body.before)
    )
    await db.commit()
    return ApiResponse(data={"deleted": result.rowcount or 0})
