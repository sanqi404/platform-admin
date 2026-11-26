"""数据库会话与 Base。

支持三种后端，通过 DATABASE_URL 切换，业务代码无需改动：
- SQLite（本地开发）   sqlite+aiosqlite:///./data/app.db
- MySQL / MariaDB      mysql+asyncmy://user:pwd@host:3306/rbac?charset=utf8mb4
- PostgreSQL           postgresql+asyncpg://user:pwd@host:5432/rbac

SQLite 无连接池概念，pool_* 参数按方言分别构造，避免传参报错。
"""
from __future__ import annotations

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

_URL = settings.DATABASE_URL
_IS_SQLITE = _URL.startswith("sqlite")

# SQLite 需要保证库文件所在目录存在
if _IS_SQLITE:
    _path = _URL.split("///")[-1]
    os.makedirs(os.path.dirname(os.path.abspath(_path)) or ".", exist_ok=True)


def _engine_kwargs() -> dict:
    kwargs: dict = {"echo": settings.DB_ECHO, "future": True, "pool_pre_ping": True}
    if _IS_SQLITE:
        return kwargs
    # 外部数据库：显式管理连接池；pool_recycle 必须小于数据库侧 wait_timeout
    kwargs.update(
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
    )
    return kwargs


engine = create_async_engine(_URL, **_engine_kwargs())

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def db_backend() -> str:
    """当前数据库方言（sqlite / mysql / postgresql），用于健康检查与日志。"""
    return engine.dialect.name


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
