"""全局配置。生产环境请通过 .env 覆盖，切勿使用默认 SECRET_KEY。"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ---- 应用 ----
    APP_NAME: str = "管理平台"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = True

    # ---- 数据库 ----
    # 本地开发默认 SQLite；生产按环境变量 DATABASE_URL 覆盖，例如
    #   MySQL:      mysql+asyncmy://user:pwd@host:3306/rbac?charset=utf8mb4
    #   PostgreSQL: postgresql+asyncpg://user:pwd@host:5432/rbac
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/app.db"
    DB_ECHO: bool = False
    # 连接池（SQLite 不生效，外部数据库按此配置）
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800   # 秒，需小于数据库侧 wait_timeout，避免拿到已被服务端断开的连接
    # 启动时是否自动建表+种子。生产建议关掉，改用 alembic upgrade head
    AUTO_CREATE_TABLES: bool = True

    # ---- 缓存 / 会话 ----
    # 留空则使用进程内缓存（仅单实例可用）。生产示例：redis://:password@127.0.0.1:6379/0
    REDIS_URL: str = ""
    CACHE_TTL: int = 180          # 权限缓存有效期（秒）
    TOKEN_BLACKLIST_ENABLED: bool = True  # 登出后立即失效 access token（依赖缓存后端）

    # ---- JWT ----
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_9f3a7c1e5b2d4f60"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ---- 安全策略 ----
    PASSWORD_MIN_LENGTH: int = 8
    LOGIN_MAX_FAIL: int = 5           # 连续失败锁定阈值
    LOGIN_LOCK_MINUTES: int = 15      # 锁定时长

    # ---- 跨域 ----
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # ---- 初始化账号 ----
    INIT_TENANT_CODE: str = "platform"
    INIT_ADMIN_USERNAME: str = "admin"
    INIT_ADMIN_PASSWORD: str = "Admin@123456"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
