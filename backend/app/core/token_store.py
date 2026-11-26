"""access token 黑名单。

JWT 无状态，签发后服务端没法提前作废；登出、改密后旧 token 在过期前仍可用，
只能靠黑名单拦截。jti 存在缓存后端，TTL 取 token 剩余有效期，到期自动清。

配置 REDIS_URL 时多副本共享，未配置时只对本进程生效（重启清空）。
"""
from __future__ import annotations

import time
from typing import Any

from app.core import cache
from app.core.config import settings

_PREFIX = "rbac:bl:"
_SESSION_PREFIX = "rbac:bl:sid:"


def _key(jti: str) -> str:
    return f"{_PREFIX}{jti}"


def _session_key(sid: str) -> str:
    return f"{_SESSION_PREFIX}{sid}"


async def revoke(payload: dict[str, Any]) -> bool:
    """按 token payload 拉黑。返回是否写入成功（无 jti 时不做处理）。"""
    if not settings.TOKEN_BLACKLIST_ENABLED:
        return False
    jti = payload.get("jti")
    if not jti:
        return False
    exp = int(payload.get("exp") or 0)
    ttl = max(1, exp - int(time.time())) if exp else settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    await cache.set_json(_key(str(jti)), {"sub": payload.get("sub"), "ts": int(time.time())}, ttl=ttl)
    return True


async def is_revoked(jti: str | None) -> bool:
    if not settings.TOKEN_BLACKLIST_ENABLED or not jti:
        return False
    return await cache.exists(_key(jti))


# --------------------------------------------------------------------------- #
# 会话级撤销：一次登出同时废掉 access + refresh，避免用 refresh 续命
# --------------------------------------------------------------------------- #
async def revoke_session(sid: str | None, ttl: int | None = None) -> bool:
    """按会话 ID 拉黑，TTL 默认覆盖 refresh 有效期。"""
    if not settings.TOKEN_BLACKLIST_ENABLED or not sid:
        return False
    if ttl is None:
        ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    await cache.set_json(_session_key(sid), {"ts": int(time.time())}, ttl=max(1, ttl))
    return True


async def is_session_revoked(sid: str | None) -> bool:
    if not settings.TOKEN_BLACKLIST_ENABLED or not sid:
        return False
    return await cache.exists(_session_key(sid))
