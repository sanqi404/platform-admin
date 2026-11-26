"""统一缓存层：配置 REDIS_URL 走 Redis，否则降级为进程内缓存。

多实例部署必须配 REDIS_URL，权限缓存与 token 黑名单都要跨实例可见；
进程内实现只在单机开发时用，重启即失效。
对外只暴露 JSON 级接口（get_json / set_json），调用方不关心后端差异。
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# 进程内实现（本地开发用）
# --------------------------------------------------------------------------- #
class _MemoryBackend:
    def __init__(self) -> None:
        # {key: (expire_ts, value)}，expire_ts=0 表示永不过期
        self._data: dict[str, tuple[float, str]] = {}
        self._lock = asyncio.Lock()

    async def ping(self) -> bool:
        return True

    async def get(self, key: str) -> Optional[str]:
        async with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            exp, value = item
            if exp and exp <= time.time():
                self._data.pop(key, None)
                return None
            return value

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        async with self._lock:
            self._data[key] = (time.time() + ttl if ttl else 0.0, value)

    async def delete(self, *keys: str) -> int:
        async with self._lock:
            return sum(1 for k in keys if self._data.pop(k, None) is not None)

    async def delete_prefix(self, prefix: str) -> int:
        async with self._lock:
            targets = [k for k in self._data if k.startswith(prefix)]
            for k in targets:
                self._data.pop(k, None)
            return len(targets)

    async def incr(self, key: str, ttl: Optional[int] = None) -> int:
        async with self._lock:
            item = self._data.get(key)
            exp, value = item if item else (0.0, "0")
            if exp and exp <= time.time():
                value, exp = "0", (time.time() + ttl if ttl else 0.0)
            nxt = int(value) + 1
            if not exp and ttl:
                exp = time.time() + ttl
            self._data[key] = (exp, str(nxt))
            return nxt

    async def close(self) -> None:
        async with self._lock:
            self._data.clear()


# --------------------------------------------------------------------------- #
# Redis 实现
# --------------------------------------------------------------------------- #
class _RedisBackend:
    def __init__(self, client: Any) -> None:
        self._c = client

    async def ping(self) -> bool:
        return bool(await self._c.ping())

    async def get(self, key: str) -> Optional[str]:
        return await self._c.get(key)

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        if ttl:
            await self._c.set(key, value, ex=ttl)
        else:
            await self._c.set(key, value)

    async def delete(self, *keys: str) -> int:
        if not keys:
            return 0
        return int(await self._c.delete(*keys))

    async def delete_prefix(self, prefix: str) -> int:
        removed = 0
        batch: list[str] = []
        async for key in self._c.scan_iter(match=f"{prefix}*", count=500):
            batch.append(key)
            if len(batch) >= 500:
                removed += int(await self._c.delete(*batch))
                batch.clear()
        if batch:
            removed += int(await self._c.delete(*batch))
        return removed

    async def incr(self, key: str, ttl: Optional[int] = None) -> int:
        value = int(await self._c.incr(key))
        if value == 1 and ttl:
            await self._c.expire(key, ttl)
        return value

    async def close(self) -> None:
        await self._c.aclose()


# --------------------------------------------------------------------------- #
# 门面
# --------------------------------------------------------------------------- #
_backend: _MemoryBackend | _RedisBackend | None = None


async def init_cache() -> str:
    """建立缓存后端，返回实际生效的后端名（redis / memory）。"""
    global _backend
    if _backend is not None:
        return "redis" if isinstance(_backend, _RedisBackend) else "memory"

    if not settings.REDIS_URL:
        _backend = _MemoryBackend()
        logger.warning("未配置 REDIS_URL，使用进程内缓存：多实例部署下权限缓存与 token 黑名单将各自独立")
        return "memory"

    try:
        from redis.asyncio import from_url

        client = from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        await client.ping()
        _backend = _RedisBackend(client)
        logger.info("缓存后端已连接 Redis")
        return "redis"
    except Exception as exc:  # 连接失败降级，避免因缓存不可用导致整站起不来
        logger.error("Redis 连接失败（%s），临时降级为进程内缓存", exc)
        _backend = _MemoryBackend()
        return "memory"


async def close_cache() -> None:
    global _backend
    if _backend is not None:
        await _backend.close()
        _backend = None


def _get() -> _MemoryBackend | _RedisBackend:
    if _backend is None:
        # 未调用 init_cache 时自动初始化，避免业务侧直接 500
        raise RuntimeError("缓存未初始化：应在应用 lifespan 中调用 init_cache()")
    return _backend


def cache_kind() -> str:
    return "redis" if isinstance(_backend, _RedisBackend) else "memory"


async def get_json(key: str) -> Any | None:
    raw = await _get().get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("缓存值非合法 JSON，已丢弃：%s", key)
        await _get().delete(key)
        return None


async def set_json(key: str, value: Any, ttl: Optional[int] = None) -> None:
    await _get().set(key, json.dumps(value, ensure_ascii=False, default=str), ttl or settings.CACHE_TTL)


async def delete(*keys: str) -> int:
    return await _get().delete(*keys)


async def delete_prefix(prefix: str) -> int:
    return await _get().delete_prefix(prefix)


async def incr(key: str, ttl: Optional[int] = None) -> int:
    return await _get().incr(key, ttl)


async def exists(key: str) -> bool:
    return await _get().get(key) is not None
