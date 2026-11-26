"""运维命令行（不含 Web 服务）：

    python -m app.manage check     # 连通性自检：数据库 + 缓存
    python -m app.manage create    # 仅按模型建表（等价 alembic upgrade head 的建表效果）
    python -m app.manage seed      # 仅写种子数据（权限点/菜单/超管/租户），可重复执行
    python -m app.manage initdb    # create + seed（首次安装）

生产推荐：alembic upgrade head → python -m app.manage seed
"""
from __future__ import annotations

import asyncio
import sys


def _mask_url(url: str) -> str:
    """隐藏连接串中的密码，便于安全打印。"""
    if "@" not in url:
        return url
    head, tail = url.rsplit("@", 1)
    if ":" not in head:
        return url
    scheme_user, _ = head.rsplit(":", 1)
    return f"{scheme_user}:***@{tail}"


async def cmd_check() -> int:
    from sqlalchemy import text

    from app.core.cache import cache_kind, close_cache, init_cache
    from app.core.config import settings
    from app.db.session import db_backend, engine

    print(f"DATABASE_URL = {_mask_url(settings.DATABASE_URL)}")
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            ver = conn.dialect.server_version_info
        ver_str = ".".join(str(x) for x in ver) if ver else "unknown"
        print(f"[OK] 数据库连通 db={db_backend()} server_version={ver_str}")
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] 数据库连接失败：{type(exc).__name__}: {exc}")
        await engine.dispose()
        return 1

    backend = await init_cache()
    print(f"[{'OK' if backend != 'memory' else 'WARN'}] 缓存后端 cache={cache_kind()}"
          + ("" if backend != "memory" else "（未配置 REDIS_URL，多实例部署必须接 Redis）"))
    await close_cache()
    await engine.dispose()
    return 0


async def cmd_create() -> int:
    from app.db.session import engine
    from app.init_db import create_tables

    await create_tables()
    print("[OK] 建表完成")
    await engine.dispose()
    return 0


async def cmd_seed() -> int:
    from app.db.session import engine
    from app.init_db import seed

    await seed(create=False)
    print("[OK] 种子数据写入完成")
    await engine.dispose()
    return 0


async def cmd_initdb() -> int:
    from app.db.session import engine
    from app.init_db import seed

    await seed(create=True)
    print("[OK] 建表 + 种子数据完成")
    await engine.dispose()
    return 0


COMMANDS = {
    "check": cmd_check,
    "create": cmd_create,
    "seed": cmd_seed,
    "initdb": cmd_initdb,
}


def main() -> int:
    action = sys.argv[1] if len(sys.argv) > 1 else "check"
    handler = COMMANDS.get(action)
    if handler is None:
        print(f"未知命令：{action}\n可用命令：{', '.join(COMMANDS)}")
        return 2
    return asyncio.run(handler())


if __name__ == "__main__":
    raise SystemExit(main())
