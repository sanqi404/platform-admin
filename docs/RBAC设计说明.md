# RBAC 权限设计说明

面向通用管理平台的权限内核设计。目标是：**租户可隔离、功能可授权、菜单可控制、数据可约束**，并且每一层的判定位置明确、可测试、可扩展。

---

## 一、设计目标与取舍

| 目标 | 做法 | 放弃的替代方案及原因 |
|---|---|---|
| 一套模型覆盖 SaaS 与私有化 | `tenant_id` 作为全表一级维度 | 单租户简化模型后期改造成本高于初期冗余一列 |
| 权限与导航分离 | `permission` 与 `menu` 两张表，菜单可选绑权限码 | 菜单即权限（menu 表当权限表用）会导致接口鉴权依赖 UI 结构，改导航就改权限 |
| 授权粒度到按钮 | 权限码 `模块:资源:动作` | 仅到页面级无法支撑"能看不能改"的常见诉求 |
| 行级数据隔离 | 角色携带 `data_scope`，查询拼条件 | 每个接口手写过滤条件易漏，统一走 `apply_data_scope` |
| 前端控制不承担安全 | 后端接口依赖强制校验 | 只靠前端隐藏，任何请求重放都能越权 |

---

## 二、数据模型

```
tenant 1 ─── n user
tenant 1 ─── n role ─── n permission      (role_permission)
tenant 1 ─── n role ─── n menu            (role_menu)
tenant 1 ─── n menu  (自关联 parent_id，type: dir/menu/button)
tenant 1 ─── n dept  (自关联 parent_id)
user    n ─── n role                       (user_role)
user    n ─── 1 dept
```

关键字段：

| 表 | 字段 | 说明 |
|---|---|---|
| `user` | `is_superuser` | 平台超管，绕过全部权限判定，权限码下发 `*:*:*` |
| `user` | `tenant_id` / `dept_id` | 租户维度 + 组织维度，后者供数据权限使用 |
| `role` | `data_scope` | 1 全部 / 2 本部门 / 3 本部门及以下 / 4 仅本人 / 5 自定义部门 |
| `role` | `custom_dept_ids` | `data_scope=5` 时生效，JSON 存部门 id |
| `menu` | `type` | `dir` 目录 / `menu` 页面 / `button` 按钮；按钮不进导航树 |
| `menu` | `perm_code` | 可选，绑定一个权限码；为空表示登录即可见 |
| `permission` | `code` | 唯一，格式 `模块:资源:动作`，如 `system:user:create` |

设计要点：

1. **`tenant_id` 全表冗余**：不做多表 join 推导租户，避免复杂查询里漏加条件。任何业务查询第一条件就是当前租户。
2. **权限码即契约**：前后端共用同一套编码，前端 `v-perm` 与后端 `require_perm` 引用字符串一致，不存在"前端叫 A 后端叫 B"。
3. **菜单与权限解耦**：同一个权限码可以绑给多个入口（例如 `system:user:list` 既用于用户管理菜单，也用于选择用户弹窗的权限）。

---

## 三、判定链路

### 1. 登录 → 下发给前端

`POST /api/v1/auth/login` 校验租户编码 + 用户名 + 密码，签发 access / refresh token（token 内含 `sub`、`tenant_id`、`type`）。

`GET /api/v1/auth/profile` 返回一次性的权限快照：

```json
{
  "user": { "id": 1, "username": "admin", "is_superuser": true },
  "tenant": { "code": "platform", "name": "平台租户" },
  "roles": ["super_admin"],
  "permissions": ["*:*:*"],
  "menus": [ { "id": 1, "title": "工作台", "path": "/dashboard", "children": [] } ],
  "data_scope": 1
}
```

前端只依赖这份快照做渲染与按钮控制，不在本地做权限推导。

### 2. 每次请求 → 后端校验

```
请求 → HTTPBearer 取 token → 解 JWT 校验 type=access
     → 查 user，校验 status=1 且 user.tenant_id == token.tenant_id   （防跨租户 token）
     → 取租户，校验 status=1                                          （租户停用即全站 403）
     → 聚合权限（命中缓存则直接返回）
     → require_perm(...) 校验权限码 → 通过则进入业务
     → 业务查询套 apply_data_scope                                     （行级过滤）
```

权限聚合规则（`services/permission.py::build_user_perm_payload`）：

- 超管：`permissions=["*:*:*"]`，`data_scope=1`，菜单取全部启用项。
- 普通用户：`permissions` = 所有 **status=1** 角色的权限并集；`roles` = 角色码集合；`data_scope` = 各角色中的 **最小值**（数值越小范围越大，取最宽松）；菜单 = 各角色授权菜单去重后按 `sort` 排序。
- 判定函数 `has_permission(perms, required, mode)`：命中 `*:*:*` 直接 True；`mode="any"` 任一命中，`mode="all"` 全部命中。

### 3. 缓存与失效

- 进程内缓存 `{user_id: (expire_ts, payload)}`，TTL 180 秒。
- `invalidate_user(user_id)`：单用户失效（如改密、停用）。
- `invalidate_tenant(tenant_id)`：角色权限变更、角色授权保存、角色删除时调用，按租户批量清空。
- 多进程/多实例部署时，把这两个函数替换为 Redis 实现（key 前缀 `perm:{tenant_id}:{user_id}`，失效用 `SCAN` + `UNLINK`），其余代码无需改动。

---

## 四、四层权限的落点

| 层 | 落点 | 实现 |
|---|---|---|
| L1 租户隔离 | `get_current_user` + 业务查询 | token 里的 `tenant_id` 必须与库里用户一致；所有查询带 `tenant_id` 条件；平台级接口（租户增删）额外要求 `require_platform_admin` |
| L2 功能权限 | 接口依赖 + 前端元素 | `Depends(require_perm("system:user:create"))`；前端 `v-perm` / `hasPerm` |
| L3 菜单权限 | `role_menu` 关联 | `perm_code` 非空时，前端在拿到菜单后再校验一次权限码，防止角色授权漂移 |
| L4 数据权限 | `DataScope` + `apply_data_scope` | 见下节 |

### 数据权限用法

```python
from app.core.deps import DataScope, apply_data_scope
from app.models import User

@router.get("/users")
async def list_users(scope: DataScope, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.tenant_id == current_tenant_id)
    stmt = apply_data_scope(stmt, User, scope)      # 自动拼行级条件
    ...
```

`apply_data_scope` 的语义：

| data_scope | dept_ids | 追加条件 |
|---|---|---|
| 1 全部 | `None` | 不加条件 |
| 2 本部门 | `[user.dept_id]` | `dept_id in (...)` |
| 3 本部门及以下 | 递归收集子部门 | `dept_id in (...)` |
| 4 仅本人 | `[]` | `id == scope["user_id"]`（用户表）或业务表自身的 `user_id` 字段 |
| 5 自定义 | 角色配置的部门集合 | `dept_id in (...)` |

注意：`dept_ids == []` 且 scope != 4 时会拼 `in [-1]`，确保"没有任何可见部门"时返回空集而不是全量——这是最容易写错的一处。

---

## 五、前端控制策略

| 场景 | 手段 | 说明 |
|---|---|---|
| 路由页面 | `meta.perm` + 全局守卫 | 进入前拦截，跳 `/403?perm=xxx`；防止直接输 URL |
| 侧边栏 | 后端菜单树 + `v-if` | 无权限节点不渲染，减少信息暴露 |
| 对比/排查模式 | `v-show` | 顶栏开关键把无权限菜单保留并置灰，便于核对授权配置 |
| 按钮/表单项 | `v-perm` 指令 / `hasPerm()` | 默认移除节点，`v-perm:show` 走 `display:none` |
| 角色维度 | `v-role` / `hasRole()` | 少数按角色而非权限点区分的场景 |

通配支持：`*:*:*` 全通配；`system:*:*` 段位通配由 `hasPerm` 内部展开处理。

**边界**：前端所有判断仅影响"看得见什么"，接口安全始终由后端 `require_perm` 兜底。任何"前端藏起来就行"的实现都视为缺陷。

---

## 六、扩展指南

### 新增一个权限点

1. `init_db.py` 的权限点清单追加 `{"code": "ops:host:restart", "name": "重启主机", "group": "运维"}`。
2. 目标接口加 `dependencies=[Depends(require_perm("ops:host:restart"))]`。
3. 前端按钮加 `v-perm="'ops:host:restart'"`。
4. 进「角色权限 → 分配权限」勾选保存，用户重新登录后生效。
5. 需要新菜单时，在菜单清单里加一条并绑定同一 `perm_code`。

### 新增一个业务表

- 表必须含 `tenant_id`，所有查询第一条件带它。
- 需要行级隔离时再加 `dept_id` / `user_id`，接口注入 `DataScope` 并调 `apply_data_scope`。
- 不建独立权限表，复用 `permission` 字典。

### 接入部门树

`dept` 表已按 `parent_id` 自关联，`resolve_dept_ids` 已实现"本部门及以下"的递归收集。前端补一个部门树管理页即可，权限模型无需改动。

---

## 七、已知边界与后续可做

| 项 | 现状 | 建议 |
|---|---|---|
| 权限缓存 | 进程内字典 | 多实例部署换 Redis |
| 登录锁定 | 按 `LOGIN_MAX_FAIL` / `LOGIN_LOCK_MINUTES` 记录失败次数 | 分布式部署时计数放 Redis |
| 数据权限 | 支持部门/本人/自定义 | 若需按字段级脱敏，在 `apply_data_scope` 旁加输出层投影 |
| 审计日志 | 未内置 | 建议在 `require_perm` 外层加操作日志中间件，记录 who/what/when/result |
| 租户套餐 | 未内置（权限点全量） | 可加 `tenant.package_id`，在权限聚合时与套餐权限点取交集 |
