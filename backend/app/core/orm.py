"""ORM 异步辅助。

异步 session 下给已持久化对象的关联集合直接赋值，会触发同步 lazy load
进而抛 MissingGreenlet；这里统一先显式 await 加载，再赋值。
"""
from __future__ import annotations

from typing import Iterable

from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession


async def ensure_loaded(db: AsyncSession, obj, names: Iterable[str]) -> None:
    """对 persistent 对象，按需异步加载指定关系属性。"""
    insp = sa_inspect(obj)
    if not insp.persistent:
        return
    unloaded = insp.unloaded
    todo = [n for n in names if n in unloaded]
    if todo:
        await db.refresh(obj, attribute_names=todo)
