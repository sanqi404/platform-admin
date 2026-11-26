# 外置数据源与中间件接入说明

本文档对应「把 SQLite 单机改造为外置数据源（MySQL / PostgreSQL）+ 引入 Redis」的落地结果，含改造点、切换步骤、验证结论与待办。

## 一、改造总览

| 能力 | 改造前 | 改造后 |
|---|---|---|
| 数据库 | 硬编码 `sqlite+aiosqlite:///./data/app.db` | `DATABASE_URL` 环境变量驱动，支持 MySQL / PostgreSQL / SQLite |
| 连接池 | 无（SQLite 单连接） | 外置库启用 `pool_size / max_overflow / pool_timeout / pool_recycle` |
| 建表方式 | 启动即 `create_all` | Alembic 版本化迁移，`AUTO_CREATE_TABLES` 控制是否兜底建表 |
| 复合索引 | 无 | 9 个租户维度复合索引（外部库生效，SQLite 自动跳过） |
| 权限缓存 | 进程内 dict + 180s TTL | 缓存后端抽象：Redis（多实例共享）/ 内存（无 Redis 时降级） |
| 登出失效 | 无（JWT 到期才失效） | jti 单令牌黑名单 + sid 会话级撤销 + refresh 轮换 |
| 健康检查 | `{"status":"up"}` | 附带实际 `db` 方言与 `cache` 后端，便于探针判断 |

### 新增 / 变更文件

```
backend/
├── alembic.ini                       # 新增：不在 ini 写 URL，避免密码含 % 触发插值
├── alembic/
│   ├── env.py                        # 新增：复用 settings.DATABASE_URL，异步引擎
│   └── versions/
│       ├── 0001_baseline.py          # 新增：基线建表
│       └── 0002_perf_indexes.py      # 新增：复合索引（sqlite 跳过）
├── docker-compose.yml                # 新增：mysql 8.4 + redis 7.4
├── .env.example                      # 新增：数据源 / 连接池 / 缓存 / 黑名单开关
├── app/manage.py                     # 新增：check / create / seed / initdb 命令行
├── app/core/cache.py                 # 新增：缓存门面（memory / redis 双后端）
├── app/core/token_store.py           # 新增：jti + sid 撤销
├── app/core/config.py                # 变更：DB_POOL_* / REDIS_URL / CACHE_TTL / AUTO_CREATE_TABLES…
├── app/db/session.py                 # 变更：按方言分支构造 engine，新增 db_backend()
├── app/services/permission.py        # 变更：权限缓存改为异步外部缓存
├── app/core/deps.py                  # 变更：校验 jti + sid 撤销
├── app/core/security.py              # 变更：create_refresh_token 支持附加 sid
├── app/api/auth.py                   # 变更：登录发 sid、refresh 轮换 + 会话校验、登出撤会话
├── app/init_db.py                    # 变更：拆出 create_tables()，seed 幂等
└── app/main.py                       # 变更：lifespan 初始化缓存 / 可选自动建表 / 健康检查增强
```

## 二、切换数据源

### 1. 起中间件（本地/测试）

```bash
cd backend
docker compose up -d          # mysql:8.4 + redis:7.4
```

### 2. 配置 .env

```bash
cp .env.example .env
# 生产必须重设 SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

关键项：

```ini
# MySQL（推荐，utf8mb4 + asyncmy 驱动）
DATABASE_URL=mysql+asyncmy://rbac:rbac_pwd@127.0.0.1:3306/rbac?charset=utf8mb4

# PostgreSQL（可选）
# DATABASE_URL=postgresql+asyncpg://rbac:rbac_pwd@127.0.0.1:5432/rbac

# 本地零依赖开发
# DATABASE_URL=sqlite+aiosqlite:///./data/app.db

DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800        # 必须小于 MySQL wait_timeout，避免拿到已被服务端关闭的连接

REDIS_URL=redis://127.0.0.1:6379/0
CACHE_TTL=180
TOKEN_BLACKLIST_ENABLED=true
AUTO_CREATE_TABLES=false    # 外置库走 alembic，不用 create_all
```

### 3. 建库结构与种子数据

```bash
python -m app.manage check            # 连通性 + 版本探测
alembic upgrade head                  # 建表 + 索引 + 版本表
python -m app.manage seed             # 权限点 / 菜单 / 角色 / 管理员（幂等）
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

健康检查应返回：

```json
{"code":0,"msg":"ok","data":{"status":"up","db":"mysql","cache":"redis"}}
```

`db` 仍为 `sqlite` 或 `cache` 仍为 `memory` 时，说明 .env 未生效或 Redis 连不上（连不上会降级并打 ERROR 日志）。

### 4. 迁移已有 SQLite 数据

结构由 Alembic 负责，业务数据需单独搬：

1. `alembic upgrade head` 先把 MySQL 结构建好（**不要**再 seed 写入初始数据，等搬运完成再按需补）；
2. 用脚本按表顺序搬：`sys_tenant → sys_dept → sys_permission → sys_menu → sys_role → sys_user → sys_user_role → sys_role_permission → sys_role_menu → sys_login_log → sys_operation_log`（外键依赖顺序不可打乱）；
3. 保留原自增 ID（否则关联表 `user_id/role_id` 全错），搬完用 `ALTER TABLE ... AUTO_INCREMENT = max(id)+1` 校正；
4. 字符集统一 `utf8mb4`，连接串带 `charset=utf8mb4`。

## 三、Redis 承担什么

| 用途 | 键 | TTL | 缺失后果 |
|---|---|---|---|
| 用户权限/菜单缓存 | `rbac:perm:u:{user_id}` | `CACHE_TTL`（180s） | 每请求回查 5 张表，QPS 高时数据库压力线性放大 |
| 租户维度索引 | `rbac:perm:t:{tenant_id}` | `CACHE_TTL*2` | 改角色后无法按租户批量失效 |
| 单令牌黑名单 | `rbac:bl:{jti}` | 令牌剩余有效期 | 登出后旧 access token 仍可用 |
| 会话撤销 | `rbac:bl:sid:{sid}` | 7 天（覆盖 refresh 有效期） | 登出后可用 refresh 换新 access，等于没登出 |

未配置 `REDIS_URL` 时后端自动降级为进程内缓存：**单实例功能完整，多实例会各自为政**（A 实例登出，B 实例仍认旧 token）。生产多副本部署必须接 Redis。

## 四、鉴权链路的三个加固点

1. **jti 黑名单**：登出/改密时把当前 access token 的 `jti` 写入缓存，依赖校验直接 401，不等自然过期。
2. **sid 会话撤销**：登录生成 `sid` 同时写进 access + refresh，登出按 `sid` 一次性废掉整条会话。
3. **refresh 轮换**：每次刷新都把旧 refresh token 的 `jti` 拉黑；重放旧 refresh 直接 401，已被登出的会话刷新也 401。

> 前端目前不做自动续期（401 直接回登录页），因此不存在并发刷新互相踢掉的竞态；将来加自动续期时，必须对 refresh 调用做单飞（single-flight）串行化，否则轮换机制会导致并发请求里后到的那次失败。

## 五、其他中间件：需要什么、不需要什么

### 必须（缺了不能算可交付）

| 中间件 | 作用 | 现状 |
|---|---|---|
| MySQL 8.0+ / PostgreSQL | 外置关系库 | 已接入 |
| Redis 7 | 跨实例缓存 + 会话撤销 | 已接入（可选，但多实例必配） |

### 建议（上生产前补齐）

| 中间件 | 作用 | 触发条件 |
|---|---|---|
| Nginx | 反代 + TLS + 静态资源 + gzip | 任何对外提供服务 |
| 备份任务（mysqldump / xtrabackup） | 数据库定时备份 | 有真实业务数据后 |
| Prometheus + Grafana | 指标与容量观测 | 需要 SLA/告警时，暴露 `/metrics` 需加 `prometheus-fastapi-instrumentator` |
| 集中日志（Loki / ELK） | 登录日志、操作日志之外的运行日志检索 | 多实例后本地日志不可聚合 |
| Sentry（或同类） | 异常堆栈上报 | 排障效率要求高时 |

### 按需（现在没有对应业务，先别上）

| 中间件 | 何时才需要 |
|---|---|
| MinIO / 对象存储 | 出现附件上传、报表导出归档、头像等文件存取 |
| Celery + Redis | 出现耗时任务（大批量导入、导出、通知推送），需要异步与重试；当前 Redis 可直接当 broker |
| APScheduler | 仅需定时清理日志/归档时先内嵌即可，不必上 Celery |
| RabbitMQ / Kafka | 与其他系统做事件解耦时才需要，单体平台属过度设计 |
| Elasticsearch | 操作日志全文检索量到百万级以上再考虑，MySQL 索引足够支撑当前量级 |

### 明确不需要

Nacos / Eureka（无微服务注册需求）、SkyWalking（无分布式链路）、MongoDB（无文档型数据）——这个体量引入只会增加运维负担。

## 六、验证结论（本机实测）

| 验证项 | 方法 | 结果 |
|---|---|---|
| MySQL DDL 可生成 | `alembic upgrade head --sql`（`DATABASE_URL` 指向 mysql+asyncmy） | 12 张表 + 9 个复合索引，主键 `BIGINT AUTO_INCREMENT` |
| 迁移链完整性 | 同上离线和 SQLite 在线各跑一次 | `0001_baseline → 0002_perf_indexes`，无报错 |
| SQLite 在线迁移 | 临时库 `alembic upgrade head` | 12 张表 + `alembic_version=0002_perf_indexes` |
| Redis 缓存分支 | fakeredis 替换客户端，走真实 `init_cache` 代码路径 | `cache_kind=redis`，JSON 存取 / TTL / incr / 前缀删除全部通过 |
| 会话撤销 | 起服务实测 | 登出后 access 401、refresh 401；旧 refresh 重放 401 |
| 刷新轮换 | 同上 | 首次 refresh 200，旧 refresh 二次使用 401 |
| 无 Redis 降级 | `REDIS_URL` 置空启动 | 启动打出 WARN 并降级 memory，功能正常 |

未实测项（本机无 Docker / MySQL / Redis 服务）：真实 MySQL 连接、真实 Redis 连接的端到端联调，需在目标环境执行第二节步骤验收。

## 七、已知待优化项

1. **时间字段时区**：模型用 `DateTime`（无时区），代码写 `datetime.now()`（本地时间）。多时区或跨库展示时应统一为 UTC 存储 + 展示层转换，改动面涉及全表与前端，暂未动。
2. **`ensure_loaded` 仍需保留**：异步 session 下对 persistent 对象的关系集合赋值会触发 `MissingGreenlet`，切库不改变该约束。
3. **权限缓存失效粒度**：目前按 user 与 tenant 两级；角色改动量大时 `delete_prefix` 会扫全量键，Redis 下用 `SCAN` 分批删除（每批 500），已避免 `KEYS` 阻塞。
