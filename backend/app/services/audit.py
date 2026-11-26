"""审计日志写入服务。

日志用独立会话（SessionLocal）写，不参与业务请求事务：
业务回滚不影响留痕，写日志失败只打警告，不影响主流程。
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from app.db.session import SessionLocal
from app.models import LoginLog, OperationLog

logger = logging.getLogger("app.audit")


async def write_login_log(
    *,
    tenant_id: int = 0,
    user_id: Optional[int] = None,
    username: str = "",
    login_type: str = "login",
    status: int = 1,
    fail_reason: Optional[str] = None,
    ip: str = "unknown",
    ip_region: Optional[str] = None,
    user_agent: Optional[str] = None,
    os_name: Optional[str] = None,
    browser: Optional[str] = None,
    device: Optional[str] = None,
) -> None:
    try:
        async with SessionLocal() as db:
            db.add(LoginLog(
                tenant_id=tenant_id or 0,
                user_id=user_id,
                username=(username or "")[:64],
                login_type=login_type,
                status=status,
                fail_reason=(fail_reason or None) and str(fail_reason)[:255],
                ip=(ip or "unknown")[:64],
                ip_region=ip_region,
                user_agent=user_agent,
                os=os_name,
                browser=browser,
                device=device,
                login_at=datetime.now(),
            ))
            await db.commit()
    except Exception as exc:  # 日志不可用不能拖垮认证
        logger.warning("登录日志写入失败: %s", exc)


async def write_operation_log(
    *,
    tenant_id: int = 0,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    module: str = "系统",
    action: str = "other",
    action_label: str = "",
    method: str = "",
    path: str = "",
    query: Optional[str] = None,
    target: Optional[str] = None,
    params: Optional[str] = None,
    status_code: int = 0,
    success: bool = True,
    error_msg: Optional[str] = None,
    duration_ms: int = 0,
    ip: str = "unknown",
    ip_region: Optional[str] = None,
    user_agent: Optional[str] = None,
    os_name: Optional[str] = None,
    browser: Optional[str] = None,
    device: Optional[str] = None,
) -> None:
    try:
        async with SessionLocal() as db:
            db.add(OperationLog(
                tenant_id=tenant_id or 0,
                user_id=user_id,
                username=(username or None) and str(username)[:64],
                module=module[:64],
                action=action[:32],
                action_label=action_label[:64],
                method=method[:8],
                path=path[:255],
                query=(query or None) and str(query)[:512],
                target=(target or None) and str(target)[:255],
                params=params,
                status_code=status_code,
                success=success,
                error_msg=(error_msg or None) and str(error_msg)[:255],
                duration_ms=duration_ms,
                ip=(ip or "unknown")[:64],
                ip_region=ip_region,
                user_agent=user_agent,
                os=os_name,
                browser=browser,
                device=device,
                created_at=datetime.now(),
            ))
            await db.commit()
    except Exception as exc:
        logger.warning("操作日志写入失败: %s", exc)
