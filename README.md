# RBAC 管理平台底座

一套可直接启动的管理后台底座：**多租户 + 功能权限 + 菜单权限 + 数据权限** 四层权限体系，
外加登录/操作双日志审计、JWT 双令牌会话撤销、MySQL/PostgreSQL/SQLite 可切换数据源、Redis 共享缓存。
不含任何业务模块——它只提供「加菜单、加页面、加权限点」的骨架，拿去当新项目的起点，或当作 RBAC 权限模型的参考实现。

> **许可提示（请先读）**：本项目源码公开可读，但**不授权商业使用**。作者对商用行为不提供任何形式的技术支持，
> 也不对商用产生的一切后果承担任何责任。详见 [LICENSE](LICENSE) 与文末「九、许可与商用声明」。

## 能力一览

| 能力 | 说明 |
|---|---|
| 多租户隔离 | `tenant_id` 全表冗余，请求上下文 + 服务层双重强制过滤，跨租户访问返回 403 |
| 功能权限 | 权限码 `模块:资源:动作`（如 `system:user:create`），接口依赖 + 前端指令双向校验 |
| 菜单权限 | 菜单表驱动动态路由，侧栏与路由都由后端下发，新增页面无需改前端路由文件 |
| 数据权限 | `role.data_scope` 五档（全部 / 本部门 / 本部门及以下 / 仅本人 / 自定义），当前开放两档 |
| 鉴权加固 | access + refresh 双令牌，`jti` 单令牌黑名单、`sid` 会话级撤销、refresh 每次轮换 |
| 审计日志 | 登录日志记录每次成功/失败及原因；操作日志由中间件自动采集写操作，敏感参数脱敏 |
| 数据源 | `DATABASE_URL` 驱动 MySQL 8 / PostgreSQL / SQLite 三选一，连接池可配，Alembic 版本化迁移 |
| 缓存 | 权限与黑名单缓存带 Redis / 进程内双后端，未配 Redis 自动降级为单机模式 |

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python 3.11 · FastAPI · SQLAlchemy 2（异步）· Alembic · Pydantic v2 · JWT(HS256) |
| 驱动 | `asyncmy`（MySQL）· `asyncpg`（PostgreSQL）· `aiosqlite`（SQLite）· `redis.asyncio` |
| 前端 | Vue 3 · TypeScript · Vite · Element Plus · Pinia · Vue Router |
| 中间件 | MySQL 8.0+ 或 PostgreSQL 14+ 或 SQLite；Redis 7（可选，多实例部署必配） |

## 30 秒启动（TL;DR）

```bash
# 后端：SQLite 零依赖，一条命令建表 + 造数据
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && cp .env.example .env
DATABASE_URL=sqlite+aiosqlite:///./data/app.db AUTO_CREATE_TABLES=true python -m app.init_db
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 前端（另开终端）
cd frontend && npm install && npm run dev
```

浏览器打开 <http://127.0.0.1:5173>，用 `platform` / `admin` / `Admin@123456` 登录。
需要接入 MySQL 与 Redis 时，见「二、快速启动」与「六、接入 MySQL / Redis」。

---

## 一、目录结构

```
platform-admin/
├── backend/
│   ├── app/
│   │   ├── core/           # 配置、JWT、密码哈希、依赖注入
│   │   │   ├── cache.py        # 缓存门面（redis / 进程内 memory 双后端）
│   │   │   ├── token_store.py   # jti 单令牌黑名单 + sid 会话级撤销
│   │   │   └── audit_util.py    # IP/UA 解析、参数脱敏、动作语义推断
│   │   ├── db/             # 异步引擎与会话（按方言分支构造连接池）
│   │   ├── models/         # 全部 ORM 模型（单文件，便于整体理解）
│   │   ├── schemas/        # Pydantic 出入参
│   │   ├── services/       # 权限计算服务（权限码、菜单树、数据范围）+ audit 落库
│   │   ├── api/            # auth / user / role / menu / tenant / logs 路由
│   │   ├── middleware/     # 操作日志中间件（自动记录写操作）
│   │   ├── init_db.py      # 建表 + 内置数据（权限点、菜单、角色、管理员）
│   │   ├── manage.py       # 命令行：check / create / seed / initdb
│   │   └── main.py         # 应用入口（lifespan 初始化缓存、可选兜底建表）
│   ├── alembic/
│   │   ├── env.py          # 复用 settings.DATABASE_URL 的异步迁移环境
│   │   └── versions/
│   │       ├── 0001_baseline.py        # 基线建表
│   │       └── 0002_perf_indexes.py    # 9 个租户维度复合索引（SQLite 自动跳过）
│   ├── alembic.ini         # 不在 ini 写 URL（避免密码含 % 触发插值）
│   ├── requirements.txt
│   ├── data/              # SQLite 库文件目录（运行期生成，已 gitignore）
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/            # 接口封装
│   │   ├── stores/         # Pinia：user（权限上下文）/ app（布局状态）
│   │   ├── router/         # 静态壳 + 菜单驱动的动态路由 + 全局守卫
│   │   ├── config/         # 品牌与首页配置（中性化入口）
│   │   ├── directives/     # v-perm / v-role 指令
│   │   ├── components/     # 布局、侧栏递归菜单、改密弹窗
│   │   ├── views/          # 登录 / 工作台 / 用户 / 角色 / 菜单 / 租户 / 登录日志 / 操作日志
│   │   ├── types/          # 与后端对齐的类型定义
│   │   └── utils/          # axios 封装（统一响应、401/403 处理）
│   ├── vite.config.ts      # 开发代理 /api -> http://127.0.0.1:8000
│   └── package.json
├── docker-compose.yml      # mysql:8.4 + redis:7.4，本地一键起中间件
├── sql/                    # 初始化 SQL：mysql / postgres / sqlite 三方言建表 + 基础数据
├── docs/
│   ├── RBAC设计说明.md      # 权限模型、判定链路、扩展指南
│   └── DEPLOY_DATA_SOURCE.md # 数据源切换、Redis 作用、中间件选型、验证结论
└── LICENSE                 # 非商业许可（商用不授权、不提供支持、不担责）
```

---

## 二、快速启动

### 0. 前置要求

| 依赖 | 版本 | 是否必需 |
|---|---|---|
| Python | 3.11+（3.11.9 实测） | 必需 |
| Node.js | 18+（构建 vite 5） | 必需 |
| MySQL | 8.0+ | 可选（不接就用 SQLite） |
| Redis | 7.x | 可选（不接就单机内存缓存） |
| Docker | 任意近期版本 | 可选（仅用于一键起 MySQL + Redis） |

两条启动路径，按需选一条：

| 路径 | 依赖 | 建表方式 | 适用 |
|---|---|---|---|
| A. SQLite 零配置 | 无需任何中间件 | 启动时自动建表（`AUTO_CREATE_TABLES=true`） | 本地看效果、二次开发、单元验证 |
| B. MySQL + Redis | 需 MySQL / Redis | Alembic 迁移（`AUTO_CREATE_TABLES=false`） | 演示环境、多实例、接近生产 |

### 1. 后端（路径 A：SQLite，零依赖）

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt    # 首次约 1~2 分钟

cp .env.example .env
```

打开 `.env`，把数据源两行改成下面这样（即注释掉 MySQL 行、启用 SQLite 行，并允许自动建表）：

```ini
DATABASE_URL=sqlite+aiosqlite:///./data/app.db
AUTO_CREATE_TABLES=true
SECRET_KEY=任意一段足够长的随机串
```

生成随机 `SECRET_KEY`：

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

建表 + 造数据 + 启动（`data/` 目录不存在会自动创建）：

```bash
python -m app.init_db                                    # 建 12 张表 + 初始化权限点/菜单/角色/管理员
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

看到日志 `启动完成：db=sqlite cache=memory` 即成功。

### 2. 后端（路径 B：MySQL + Redis，走迁移）

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

docker compose up -d               # 起 mysql:8.4 + redis:7.4（在仓库根目录执行；本机已有 MySQL/Redis 可跳过）
```

改 `.env` 中这几项（其余保持默认）：

```ini
DATABASE_URL=mysql+asyncmy://rbac:CHANGE_ME@127.0.0.1:3306/rbac?charset=utf8mb4
REDIS_URL=redis://127.0.0.1:6379/0
AUTO_CREATE_TABLES=false           # 外置库由 alembic 管表结构
SECRET_KEY=上面生成的随机串
```

> 密码 `CHANGE_ME` 取自 `docker-compose.yml` 里 `MYSQL_PASSWORD` 的默认值；改了 compose 的密码，这里要同步改。
> 用自己的 MySQL 实例时，换成第 1 步里设的强密码。

按顺序执行，四步不可颠倒：

```bash
python -m app.manage check         # 1. 探测连通性（打印实际 db 方言与 cache 后端）
alembic upgrade head               # 2. 建表 + 9 个复合索引 + alembic_version
python -m app.manage seed          # 3. 初始化权限点/菜单/角色/管理员（幂等，可重复跑）
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

看到日志 `启动完成：db=mysql cache=redis` 即成功。MySQL 建库与账号授权细节见「六、接入 MySQL / Redis」。

### 3. 前端

```bash
cd frontend
npm install
npm run dev        # http://127.0.0.1:5173
```

开发期由 Vite 代理 `/api` 到 `http://127.0.0.1:8000`（见 `frontend/vite.config.ts`），无需配置跨域。
后端端口不是 8000 时，同步改代理 target，或在前端建 `.env.local` 写 `VITE_API_BASE`。

### 4. 默认账号

| 租户编码 | 用户名 | 密码 | 角色 |
|---|---|---|---|
| `platform` | `admin` | `Admin@123456` | super_admin（全部权限） |

账号密码由 `.env` 的 `INIT_TENANT_CODE` / `INIT_ADMIN_USERNAME` / `INIT_ADMIN_PASSWORD` 决定，
改完重新跑 seed 即可（幂等，不会重复插入）。
只读账号可在「用户管理」中新建，或直接看内置 `viewer` 角色的授权范围（`dashboard:view` + `system:user:list`，数据范围=仅本人）。

### 5. 启动成功怎么验证

| 检查项 | 命令 / 地址 | 期望结果 |
|---|---|---|
| 后端存活 | `curl http://127.0.0.1:8000/health` | `{"code":0,"data":{"status":"up","db":"mysql","cache":"redis"}}`（SQLite 路径则 `sqlite` / `memory`） |
| 接口文档 | <http://127.0.0.1:8000/docs> | 打开 Swagger，含 `/api/v1/auth/login` 等分组 |
| 登录接口 | `curl -X POST http://127.0.0.1:8000/api/v1/auth/login -H 'Content-Type: application/json' -d '{"tenant_code":"platform","username":"admin","password":"Admin@123456"}'` | 返回 `code:0` 与 `access_token` |
| 前端可用 | <http://127.0.0.1:5173> | 出现登录页，登录后侧栏按菜单表渲染 |

`health` 里的 `db` 与 `cache` 是排查配置是否生效的第一现场：期望 `mysql` 却返回 `sqlite`，说明 `.env`
没被读到或 `DATABASE_URL` 仍被注释；期望 `redis` 却返回 `memory`，说明 Redis 连不上（启动日志有 WARN/ERROR）。

### 6. 启动报错速查

| 现象 | 原因与处理 |
|---|---|
| `Address already in use` | 端口被占。后端换 `--port 8001`，或 `lsof -i :8000` 找到进程后停掉 |
| `ModuleNotFoundError: app` | 不在 `backend/` 目录执行，或虚拟环境未激活 |
| `psycopg2` / `asyncmy` 缺失 | 未装 `requirements.txt`，或用了别的 Python 环境；重新 `pip install -r requirements.txt` |
| `RuntimeError: greenlet` 相关 | 未安装 SQLAlchemy 异步依赖，重装 requirements |
| 登录返回 403 / 菜单为空 | 没跑 seed（权限点与菜单未初始化），执行 `python -m app.manage seed` |
| 迁移报 `Can't locate revision` | `alembic/versions` 缺失或不在 `backend/` 目录执行 |
| 前端 404 到后端 | 后端未启动，或端口与 `vite.config.ts` 代理 target 不一致 |

---

## 三、权限模型（四层）

| 层级 | 维度 | 载体 | 生效位置 |
|---|---|---|---|
| L1 | 租户隔离 | `tenant_id` 全表冗余 | 请求上下文 + 服务层强制过滤 |
| L2 | 功能权限 | `permission.code = 模块:资源:动作` | 接口依赖 + 前端按钮/指令 |
| L3 | 菜单权限 | `role_menu` + `menu.perm_code` | 侧边栏渲染 |
| L4 | 数据权限 | `role.data_scope`（1~5） | 查询行级过滤 |

> 底座当前未启用部门管理，角色界面只开放「全部数据 / 仅本人数据」两档；2/3/5 三档依赖部门树，
> 后端枚举与判定逻辑完整保留，接入部门后把 `types/index.ts` 里 `DATA_SCOPE_SELECTABLE` 的过滤条件放开即可。

要点：

- **权限与菜单解耦**：`permission` 表只描述能力，`menu` 表描述导航。一个菜单可绑定一个权限码，也可以不绑（仅需登录）。
- **多角色取并集**：用户权限 = 所有启用角色的权限集合 ∪ 数据范围取最宽。
- **超级通配**：`is_superuser` 的用户直接下发 `*:*:*`，判定时短路通过。
- **缓存与失效**：权限按 `user_id` 缓存 180 秒；角色变更、授权保存时按 `tenant_id` 批量失效，避免逐个清缓存。
- **前端只做体验层**：所有判定最终以接口依赖为准，前端隐藏不构成安全边界。

详细说明见 `docs/RBAC设计说明.md`。

---

## 四、前端权限控制方式

四种粒度，按场景选用：

### 1. 路由级（页面）

页面路由不写在代码里，而是由后端菜单表驱动：登录后 `registerMenuRoutes()` 按菜单的
`path` / `component` / `perm_code` 调 `addRoute` 注册，守卫再按 `meta.perm` 拦截，无权限跳 `/403`。

```ts
// 菜单表一行 → 一条路由
{ title: '用户管理', path: '/system/user', component: 'system/user/index', perm_code: 'system:user:list' }
```

因此**新增页面不需要改 `router/index.ts`**，见第五章。

### 2. 菜单级（侧边栏）

由后端 `/auth/profile` 返回的菜单树驱动，前端再用 `perm_code` 二次校验：

```vue
<!-- components/SidebarItem.vue -->
<el-menu-item v-if="allowed" :index="item.path">...</el-menu-item>
```

顶栏不再提供「显示无权限菜单」演示开关：无权限菜单一律不进入 DOM，避免暴露节点结构。

### 3. 元素级（按钮）

**推荐：指令**

```vue
<el-button v-perm="'system:user:create'">新建</el-button>        <!-- 无权限 → 移除节点（类 v-if） -->
<el-button v-perm:show="'system:user:update'">编辑</el-button>   <!-- 无权限 → display:none（类 v-show） -->
<el-button v-perm="['a:b:c', 'a:b:d']">任一命中</el-button>
<el-button v-perm.all="['a:b:c', 'a:b:d']">全部命中</el-button>
<el-button v-role="'super_admin'">仅超管</el-button>
```

**等价写法**

```vue
<el-button v-if="user.hasPerm('system:user:create')">新建</el-button>
<el-button v-show="user.hasPerm('system:user:update')">编辑</el-button>
```

### 4. 编程式

```ts
const user = useUserStore()
if (user.hasPerm('system:role:grant')) { ... }
if (user.hasAnyPerm(['a:b:c', 'a:b:d'])) { ... }
```

### v-if 还是 v-show？选型建议

| 场景 | 选择 | 原因 |
|---|---|---|
| 侧边栏菜单 | `v-if` | 无权限节点不应进入 DOM，减少信息暴露；菜单量小、切换不频繁 |
| 表格行内按钮 | 指令（默认移除） | 批量渲染省节点，可读性优于重复写表达式 |
| 高频切换的状态块 | `v-show` | 仅切 `display`，避免反复销毁重建、丢失表单状态 |
| 路由页面 | 守卫 `meta.perm` | 进入前拦截，比渲染后隐藏更安全 |
| 接口数据 | 后端校验 | 前端判断可绕过，权限必须后端兜底 |

---

## 五、怎么加一个菜单 / 一个页面

三步，全程不碰 `router/index.ts`。

### 1. 建页面文件

路径即菜单的 `component`，两种写法都支持（`src/views` 下自动扫描）：

```
src/views/asset/host/index.vue      → 菜单 component 填 asset/host/index
src/views/asset/host.vue            → 菜单 component 填 asset/host.vue
```

页面内按钮用权限指令，列表沿用统一 axios 封装：

```vue
<el-button v-perm="'asset:host:create'" type="primary">新增主机</el-button>
```

### 2. 加菜单（后端 `app/init_db.py`，重跑即生效）

```python
# 权限点：模块:资源:动作
("asset:host:list", "主机查询", "asset", "主机"),
("asset:host:create", "主机新增", "asset", "主机"),

# 菜单：dir 分组 → menu 页面 → button 按钮
{"title": "资产管理", "name": "Asset", "path": "/asset", "type": "dir", "icon": "Box", "children": [
    {"title": "主机列表", "name": "AssetHost", "path": "/asset/host",
     "component": "asset/host/index", "type": "menu", "perm_code": "asset:host:list",
     "children": [
         {"title": "新增", "name": "AssetHostCreate", "type": "button",
          "perm_code": "asset:host:create"},
     ]},
]},
```

```bash
cd backend && python -m app.init_db     # 幂等，可反复执行
```

### 3. 授权并验收

用 admin 登录 → 「角色权限 → 分配权限」勾上新权限点与菜单 → 保存 → 目标账号重新登录
（或刷新页面）即可在侧边栏看到入口，直接访问 `/asset/host` 也放行。

> 只想让页面进得去、按钮不加控制时，菜单的 `perm_code` 留空即可（表示只需登录）。
> 接口侧记得用 `Depends(require_perm('asset:host:list'))` 兜底，前端隐藏不构成安全边界。

### 加菜单时容易踩的三个点

| 现象 | 原因 |
|---|---|
| 侧边栏有，点进去 404 | 菜单 `component` 与 `views` 下真实文件路径不一致 |
| 点进去 403 | 菜单 `perm_code` 有值但角色未授权 |
| 刷新后 404、再点一次又正常 | 动态路由注册顺序问题，本项目已在守卫里 `replace` 重走一次解决，自定义守卫时别破坏这段逻辑 |

---

## 五之二、日志审计

### 登录日志（`sys_login_log`）

`POST /auth/login` 的每个分支都落库：租户不存在 / 已停用 / 已过期 / 账号不存在 / 锁定中 /
账号停用 / 密码错误 / 成功。字段含账号、时间、成功与否、失败原因、来源 IP 及归属
（本机/内网/公网）、操作系统、浏览器、设备类型。

### 操作日志（`sys_operation_log`）

由 `OperationLogMiddleware` 自动采集，拦截 `POST/PUT/PATCH/DELETE` 以及路径含 `export` 的 GET，
记录：账号、模块、动作语义（新增用户 / 删除角色 / 分配权限给角色 …）、请求方法、路径、查询串、
操作对象、**脱敏后的请求参数**、状态码、成功标志、耗时、IP/归属、UA 解析结果。

- 敏感字段（`password` / `token` / `secret` / `api_key` 等）统一替换为 `******`，超长截断 4000 字符；
- 业务失败（4xx/5xx）同样留痕，排查时能看到「谁尝试做了什么、为什么没成」；
- 日志写入走独立会话，写日志失败只打警告，绝不影响业务响应。

### 接口与权限

| 接口 | 权限码 |
|---|---|
| `GET /logs/login`、`GET /logs/operation`、`GET /logs/operation/{id}` | `system:loginlog:list` / `system:operlog:list` |
| `DELETE /logs/login/{id}`、`DELETE /logs/operation/{id}` | `system:loginlog:delete` / `system:operlog:delete` |
| `POST /logs/login/clean`、`POST /logs/operation/clean`（按时间点批量清理） | 同上 delete |

全部按当前账号的 `tenant_id` 过滤，跨租户访问返回 403。

---

## 六、接入 MySQL / Redis

数据源由 `DATABASE_URL` 单一变量驱动，业务代码零改动即可换库。三种连接串：

| 数据库 | 连接串格式 | 驱动（已在 requirements.txt） |
|---|---|---|
| MySQL 8 / MariaDB | `mysql+asyncmy://用户:密码@主机:3306/库名?charset=utf8mb4` | `asyncmy==0.2.10` |
| PostgreSQL | `postgresql+asyncpg://用户:密码@主机:5432/库名` | `asyncpg==0.30.0` |
| SQLite（默认） | `sqlite+aiosqlite:///./data/app.db` | `aiosqlite` |

> 驱动必须是**异步**的：MySQL 用 `asyncmy`（写成 `aiomysql` / `pymysql` / `mysqlclient` 会在建引擎时直接报错），
> PostgreSQL 用 `asyncpg`（不是 `psycopg2`）。

### 1. 接入 MySQL：五步

**第 1 步：准备库与账号**（已有实例可跳过；用 `docker compose up -d` 时容器已自动建好 `rbac` 库与 `rbac` 账号，密码取自 compose 的 `MYSQL_PASSWORD`，默认 `CHANGE_ME`）

```sql
CREATE DATABASE rbac DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER 'rbac'@'%' IDENTIFIED BY '你的强密码';
GRANT ALL PRIVILEGES ON rbac.* TO 'rbac'@'%';
FLUSH PRIVILEGES;
```

字符集必须是 `utf8mb4`，排序规则建议 `utf8mb4_0900_ai_ci`（MySQL 8 默认），否则中文与 emoji 会出现乱码或写入报错。

**第 2 步：改 `.env`**

```ini
DATABASE_URL=mysql+asyncmy://rbac:你的强密码@127.0.0.1:3306/rbac?charset=utf8mb4
AUTO_CREATE_TABLES=false        # 外置库交给 alembic，不要用 create_all
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800            # 必须小于 MySQL 的 wait_timeout（compose 里是 28800）
```

密码里带 `@`、`/`、`%`、`#` 等字符时必须 URL 编码（如 `@` → `%40`）。`alembic.ini` 故意不写 URL，就是为了避免 `%` 被 configparser 当插值符吞掉——密码统一只在 `.env` 里维护一份。

**第 3 步：探连通性**

```bash
python -m app.manage check
```

输出应显示实际方言为 `mysql` 与服务器版本。连不上时优先查：MySQL 是否允许该用户从当前主机登录、3306 是否放行、密码是否需要 URL 编码。

**第 4 步：建表 + 索引 + 种子数据**

```bash
alembic upgrade head        # 12 张表 + 9 个复合索引 + alembic_version
python -m app.manage seed   # 权限点 / 菜单 / 角色 / 管理员（幂等）
```

`alembic upgrade head` 只建结构、不写业务数据；`seed` 只写初始数据、不建表。两者职责分开，顺序不可颠倒。

**第 5 步：启动并验证**

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
curl http://127.0.0.1:8000/health
# {"code":0,"msg":"ok","data":{"status":"up","db":"mysql","cache":"redis"}}
```

`db` 显示 `mysql` 才算真正切过去。仍显示 `sqlite` 时，检查是否在 `backend/` 目录启动、`.env` 是否被 `.env.local` 覆盖、`DATABASE_URL` 是否被上一行注释符留在原地。

### 2. 已有 SQLite 数据要搬到 MySQL

结构靠 Alembic，数据得单搬。顺序与坑：

1. 先 `alembic upgrade head` 把 MySQL 结构建好，**先不要跑 seed**；
2. 按外键依赖顺序搬表：
   `sys_tenant → sys_dept → sys_permission → sys_menu → sys_role → sys_user → sys_user_role → sys_role_permission → sys_role_menu → sys_login_log → sys_operation_log`；
3. **保留原自增 ID**（否则 `user_id` / `role_id` 关联全错位），搬完用 `ALTER TABLE 表名 AUTO_INCREMENT = max(id)+1` 校正；
4. 连接串务必带 `charset=utf8mb4`，目标库排序规则与源一致。

搬完再按需补 seed（幂等，不会覆盖已有记录）。

### 3. 接入 Redis：一个变量

```ini
REDIS_URL=redis://127.0.0.1:6379/0            # 无密码（compose 默认）
# REDIS_URL=redis://:你的密码@127.0.0.1:6379/0  # 有 requirepass 时
CACHE_TTL=180
TOKEN_BLACKLIST_ENABLED=true
```

改完重启后端，`/health` 的 `cache` 字段变成 `redis` 即接入成功。

Redis 在四个位置生效：

| 用途 | 键 | TTL | 不接 Redis 的后果 |
|---|---|---|---|
| 用户权限/菜单缓存 | `rbac:perm:u:{user_id}` | `CACHE_TTL`（180s） | 每次请求回查 5 张表，高并发下数据库压力线性放大 |
| 租户维度索引 | `rbac:perm:t:{tenant_id}` | `CACHE_TTL × 2` | 改角色后无法按租户批量失效，只能等自然过期 |
| 单令牌黑名单 | `rbac:bl:{jti}` | 令牌剩余有效期 | 登出后旧 access token 仍可用至过期 |
| 会话撤销 | `rbac:bl:sid:{sid}` | 7 天（覆盖 refresh 有效期） | 登出后可用 refresh 换新 access，等于没登出 |

**降级行为**：未配 `REDIS_URL` 或连接失败时，后端自动降级为进程内缓存并打 WARN/ERROR 日志，单实例功能完整。
**多实例 / 多副本部署必须接 Redis**——否则 A 实例的登出、授权变更对 B 实例无效，各进程各自为政。
生产 Redis 建议：开 `appendonly`、设 `maxmemory-policy allkeys-lru`、配密码与内网 ACL、按 business 前缀区分库（`/0` 之外另起）。

### 4. 换库时需要知道的三件事

- 模型层未使用任何 SQLite 专属语法，主键类型由 `ID_TYPE` 按方言适配（MySQL/PostgreSQL 为 `BigInteger`、SQLite 为 `Integer`），换库无需改模型；
- `0002_perf_indexes` 里的 9 个复合索引在 SQLite 上自动跳过、在外置库生效，因此"本地 SQLite 没索引"是预期行为；
- 异步 session 下对 persistent 对象的关系集合赋值会触发 `MissingGreenlet`，代码里的 `ensure_loaded` 不能删，换库不改变该约束。

数据源切换的完整背景、验证结论与中间件选型建议，见 [docs/DEPLOY_DATA_SOURCE.md](docs/DEPLOY_DATA_SOURCE.md)。

### 5. 不走 Alembic：直接导 `sql/` 下的脚本

DBA 审核、离线交付或由别的平台统一建库时，可以跳过 Alembic 直接导入 SQL。`sql/` 下按方言分 `mysql`、`postgres`、`sqlite` 三个目录，每个目录都是 `01_schema.sql`（建表 + 9 个复合索引）+ `02_seed.sql`（基础数据），内容与迁移结果一致，细则见 [sql/README.md](sql/README.md)。

```bash
mysql -u root -p < sql/mysql/01_schema.sql
mysql -u root -p rbac < sql/mysql/02_seed.sql
```

导完后把 `.env` 的 `AUTO_CREATE_TABLES` 设为 `false`，直接起服务即可。之后模型再有改动，建议回到 Alembic 维护，两条路不要混用。

---

## 七、常见问题

### macOS 上 `vite build` 报 rollup 原生模块 dlopen 失败

现象：`Error: dlopen(... rollup.darwin-arm64.node ...) different Team IDs` / `Trying to load an unsigned library`。

原因：所用 node 二进制带 Team ID 签名（常见于 App 内置 node、部分打包分发版），而 npm 装的 rollup 原生库是 adhoc 签名，macOS 的库校验拒绝混合签名。

处理（任选其一）：

```bash
# 方案 A：换用系统/Homebrew 的 node 执行构建
PATH=/opt/homebrew/bin:$PATH npm run build

# 方案 B：给原生库重新做 adhoc 签名，使其与 node 一致
codesign --force --sign - node_modules/@rollup/rollup-darwin-*/rollup.*.node
```

注意 `codesign --remove-signature` 会变成"无签名库"同样被拒，必须重新 `--sign -`。

### 端口冲突

后端默认 8000，前端 5173，代理目标写在 `frontend/vite.config.ts`。改后端端口时同步改代理 target，或前端建 `.env.local` 写 `VITE_API_BASE`（如使用绝对地址需后端 `CORS_ORIGINS` 放行）。

### 改了角色权限但前端没变化

权限快照在登录时下发，且后端有 180 秒缓存。授权保存时已按租户批量失效，前端重新登录（或刷新拿到新 profile）即可看到变化。

## 八、生产部署要点

- `SECRET_KEY` 必须替换，`DEBUG=false`。
- 前端 `npm run build` 产出 `dist/`，由 Nginx 托管并把 `/api` 反代到后端。
- 后端以 `gunicorn -k uvicorn.workers.UvicornWorker` 多进程运行；权限缓存若需跨进程共享，把 `services/permission.py` 里的进程内缓存换成 Redis。
- 初始化账号 `admin` 首次登录后立即改密；只读/值班类账号按最小权限建角色。

---

## 九、许可与商用声明

本项目**源码公开，但仅授权非商业使用**。完整条款见 [LICENSE](LICENSE)，此处为中文摘要（以 LICENSE 正文为准）：

| 事项 | 结论 |
|---|---|
| 个人学习 / 技术研究 / 教学演示 / 技术评估 | **允许**，可自由阅读、复制、修改、部署 |
| 二次开发后用于上述非商业场景 | **允许**，须保留 LICENSE 与版权声明 |
| 对外销售、收费分发、按量/订阅计费 | **不允许**，需作者书面授权 |
| 作为 SaaS / 云服务 / 托管服务对外提供 | **不允许**，需作者书面授权 |
| 集成进对外销售的产品或客户交付项目 | **不允许**，需作者书面授权 |
| 营利性组织内部生产经营系统使用 | **不允许**，需作者书面授权 |
| 以本项目为基础承接实施、定制、运维、培训等收费服务 | **不允许**，需作者书面授权 |

**作者明确不承担的**：

1. **不提供任何支持**——商业使用不附带技术答疑、缺陷修复、安全响应、版本升级、兼容性保障、上线协助或 SLA；
2. **不承担任何责任**——软件按「现状」提供，无任何明示或默示担保；因使用本软件（无论是否商用）产生的数据丢失、业务中断、利润损失、第三方索赔、合规处罚等一切后果，均由使用者自行承担，与作者无关；
3. 使用者自行负责部署环境、数据备份、安全加固、账号密钥管理与所在地法律法规合规。

违反许可条款（尤其是未经授权商用）时，授权立即自动终止，须停止使用并销毁全部副本；作者保留追究法律责任的权利。
需要商业授权或付费支持，请联系作者。
