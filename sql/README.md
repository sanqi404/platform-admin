---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 9050c8968b179f6a41587a8c58f33663_64151c89e95c11f1aa8b525400dc9a98
    ReservedCode1: G27ffUHontkOni5O2cljoM0crT4tjx/VJTcHaMfiFA5IEd/+X2ni5rGbFxS8/E0FYR3hU24VJL/EgF8nea5x/WP3zRAuM4WKKHQ6DH943X70I8PjuXgLFrIra3V9KZwbTs4uPCKLGoD8vRitHEnfY6xvMuw5j6izsApP2bRsRkb9JrNG90WWSufFx/w=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 9050c8968b179f6a41587a8c58f33663_64151c89e95c11f1aa8b525400dc9a98
    ReservedCode2: G27ffUHontkOni5O2cljoM0crT4tjx/VJTcHaMfiFA5IEd/+X2ni5rGbFxS8/E0FYR3hU24VJL/EgF8nea5x/WP3zRAuM4WKKHQ6DH943X70I8PjuXgLFrIra3V9KZwbTs4uPCKLGoD8vRitHEnfY6xvMuw5j6izsApP2bRsRkb9JrNG90WWSufFx/w=
---

# 初始化 SQL

由 `backend/app/models` 与种子数据导出，结果与 `backend/alembic` 迁移一致。给不走 Alembic 的场景用：DBA 审核后执行、离线交付、由其他平台导入建库。

| 目录 | 方言 | 说明 |
|---|---|---|
| `mysql/` | MySQL 8.0+ | `01_schema.sql` 建库 + 建表 + 9 个复合索引，`02_seed.sql` 基础数据 |
| `postgres/` | PostgreSQL 14+ | 先 `CREATE DATABASE rbac;`，连到 `rbac` 库再执行 |
| `sqlite/` | SQLite 3 | 单文件库，本地起服务用 |

## 执行顺序

两个文件必须按序执行，`02_seed.sql` 依赖 `01_schema.sql` 建好的表。

```bash
# MySQL
mysql -u root -p < mysql/01_schema.sql
mysql -u root -p rbac < mysql/02_seed.sql

# PostgreSQL
createdb rbac
psql -d rbac -f postgres/01_schema.sql
psql -d rbac -f postgres/02_seed.sql

# SQLite
sqlite3 rbac.db < sqlite/01_schema.sql
sqlite3 rbac.db < sqlite/02_seed.sql
```

MySQL 脚本头部已包含 `CREATE DATABASE IF NOT EXISTS rbac` 与 `SET FOREIGN_KEY_CHECKS = 0/1`，重复执行建表会因表已存在而报错，需要重建时先自行 `DROP DATABASE`。

## 基础数据内容

| 表 | 行数 | 内容 |
|---|---|---|
| `sys_tenant` | 1 | 平台租户 `platform`（账号上限 9999，长期有效） |
| `sys_user` | 1 | 初始管理员 `admin`，密码 `Admin@123456`（bcrypt 已加密） |
| `sys_role` | 2 | `admin` 超级管理员、`viewer` 只读角色 |
| `sys_permission` | 23 | 权限点字典，命名规则 `模块:资源:动作` |
| `sys_menu` | 24 | 工作台 + 系统管理菜单树，含按钮级节点 |
| `sys_role_permission` | 25 | 两个角色的功能权限授权 |
| `sys_role_menu` | 27 | 两个角色的菜单授权 |
| `sys_user_role` | 1 | admin 绑定超级管理员角色 |

`sys_dept`、`sys_login_log`、`sys_operation_log` 初始为空：部门管理未启用，日志随运行写入。

初始管理员密码写死在脚本里，部署到可访问环境后请立即改密。

## 与 Alembic 的关系

两条路二选一，不要混用：

- 用 Alembic：`alembic upgrade head` + `python -m app.manage seed`，后续表结构变更靠版本化迁移。
- 用本目录 SQL：导完即完成初始化，但后续若模型有变更，需要自己补 DDL。

模型改动后重新导出本目录的脚本，避免它与 Alembic 迁移漂移。
*（内容由AI生成，仅供参考）*
