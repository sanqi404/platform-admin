"""操作日志中间件：对写操作（增/删/改/导出）自动留痕。

只记录有副作用的请求（POST/PUT/PATCH/DELETE，外加显式导出的 GET）；
认证接口自己写登录日志，这里跳过；请求体靠 request._receive 重放读取；
日志在响应返回后写入，异常吞掉不影响响应。
- 只记录有副作用的请求（POST/PUT/PATCH/DELETE），以及显式的导出 GET；
- 认证类接口（login/logout/refresh）由 auth 接口自行写登录日志，这里跳过，避免重复；
- 通过 request._receive 重放请求体，业务侧仍能正常读取 body；
- 日志写入在响应返回后异步完成，且吞掉异常，绝不影响业务响应。
"""
from __future__ import annotations

import logging
import time
from typing import Optional, Tuple

from fastapi import Request
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.audit_util import (
    client_ip, compose_action_label, ip_region, mask_params, parse_ua,
    resolve_action, resolve_module, resolve_target,
)
from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models import User
from app.services.audit import write_operation_log

logger = logging.getLogger("app.audit")

_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# 认证链路自记登录日志，中间件不再重复记操作日志
_SKIP_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/logout",
    "/api/v1/auth/refresh",
}

# 不记录请求体的路径（体积大或无意义）
_NO_BODY_PATHS = {"/api/v1/auth/profile"}


class OperationLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not self._should_log(request):
            return await call_next(request)

        body = b""
        try:
            body = await request.body()
        except Exception:
            body = b""

        # 重放请求体，保证下游路由仍能读取
        async def _receive() -> dict:
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = _receive  # type: ignore[attr-defined]

        started = time.perf_counter()
        status_code = 500
        error_msg: Optional[str] = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as exc:
            error_msg = f"{exc.__class__.__name__}: {exc}"
            raise
        finally:
            duration_ms = int((time.perf_counter() - started) * 1000)
            try:
                await self._record(request, body, status_code, duration_ms, error_msg)
            except Exception as exc:  # 审计失败不影响主响应
                logger.warning("操作日志记录失败: %s", exc)

    # ------------------------------------------------------------------ #
    @staticmethod
    def _should_log(request: Request) -> bool:
        path = request.url.path
        if path in _SKIP_PATHS:
            return False
        if path.startswith(("/docs", "/redoc", "/openapi.json", "/health")):
            return False
        method = request.method.upper()
        if method in _WRITE_METHODS:
            return True
        # 导出属于高敏感读操作，单独留痕
        return method == "GET" and "export" in path.lower()

    async def _record(
        self,
        request: Request,
        body: bytes,
        status_code: int,
        duration_ms: int,
        error_msg: Optional[str],
    ) -> None:
        path = request.url.path
        method = request.method.upper()

        user_id, tenant_id, username = await self._resolve_user(request)

        action, action_label = resolve_action(method, path)
        module = resolve_module(path)

        ua = request.headers.get("user-agent")
        os_name, browser, device = parse_ua(ua)
        ip = client_ip(request)

        params = None
        if path not in _NO_BODY_PATHS and body:
            params = mask_params(body)

        query = request.url.query or None

        await write_operation_log(
            tenant_id=tenant_id,
            user_id=user_id,
            username=username,
            module=module,
            action=action,
            action_label=compose_action_label(module, action_label),
            method=method,
            path=path,
            query=query,
            target=resolve_target(path),
            params=params,
            status_code=status_code,
            success=200 <= status_code < 400,
            error_msg=error_msg,
            duration_ms=duration_ms,
            ip=ip,
            ip_region=ip_region(ip),
            user_agent=ua,
            os_name=os_name,
            browser=browser,
            device=device,
        )

    @staticmethod
    async def _resolve_user(request: Request) -> Tuple[Optional[int], int, Optional[str]]:
        """从 Bearer token 反解操作人，不触发权限校验，仅用于留痕。"""
        auth = request.headers.get("authorization") or ""
        if not auth.lower().startswith("bearer "):
            return None, 0, None
        token = auth.split(" ", 1)[1].strip()
        try:
            payload = decode_token(token, "access")
            user_id = int(payload.get("sub", 0))
            tenant_id = int(payload.get("tenant_id", 0))
        except Exception:
            return None, 0, None

        try:
            async with SessionLocal() as db:
                row = (await db.execute(
                    select(User.username, User.tenant_id).where(User.id == user_id)
                )).first()
            if row is None:
                return user_id, tenant_id, None
            return user_id, row.tenant_id or tenant_id, row.username
        except Exception:
            return user_id, tenant_id, None
