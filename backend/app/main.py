"""FastAPI 入口。"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

import logging

from app.core.config import settings
from app.api import auth, logs, menu, role, tenant, user
from app.middleware import OperationLogMiddleware

logger = logging.getLogger("rbac.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.cache import close_cache, init_cache
    from app.db.session import db_backend, engine
    from app.init_db import seed

    cache_backend = await init_cache()
    logger.info("启动完成：db=%s cache=%s", db_backend(), cache_backend)

    if settings.AUTO_CREATE_TABLES:
        await seed()
    else:
        logger.info("AUTO_CREATE_TABLES=false，跳过建表与种子；请先执行 alembic upgrade head")

    yield

    await close_cache()
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    description="多租户 RBAC 管理平台",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
)

# 后注册者位于更外层：审计先于 CORS 拿到原始请求信息
app.add_middleware(OperationLogMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# 统一响应格式拦截
# --------------------------------------------------------------------------- #
@app.exception_handler(StarletteHTTPException)
async def http_exc_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail
    if isinstance(detail, list):  # 校验错误直接透传
        return JSONResponse(status_code=exc.status_code,
                            content={"code": exc.status_code, "msg": "参数错误", "data": detail})
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "msg": str(detail), "data": None},
    )


@app.exception_handler(RequestValidationError)
async def validation_exc_handler(request: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(x) for x in first.get("loc", [])[1:]) or "参数"
    return JSONResponse(
        status_code=422,
        content={"code": 422, "msg": f"{field}: {first.get('msg', '校验失败')}", "data": None},
    )


# --------------------------------------------------------------------------- #
# 路由
# --------------------------------------------------------------------------- #
for r in (auth.router, user.router, role.router, menu.router, tenant.router, logs.router):
    app.include_router(r, prefix=settings.API_PREFIX)


@app.get("/health", tags=["系统"], summary="健康检查")
async def health():
    from app.core.cache import cache_kind
    from app.db.session import db_backend

    return {"code": 0, "msg": "ok", "data": {"status": "up", "db": db_backend(), "cache": cache_kind()}}
