"""权限聚合服务：用户权限集合、菜单树、数据范围、缓存失效。"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core import cache
from app.core.config import settings
from app.models import Menu, Permission, Role, User

SUPER_PERM = "*:*:*"

# 缓存键：rbac:perm:u:{user_id}       -> 权限载荷
#         rbac:perm:t:{tenant_id}     -> 该租户已缓存的 user_id 索引，供批量失效使用
_PERM_KEY = "rbac:perm:u:{uid}"
_PERM_PREFIX = "rbac:perm:u:"
_TENANT_KEY = "rbac:perm:t:{tid}"
_MENU_FIELDS = (
    "id", "parent_id", "title", "name", "path", "component",
    "icon", "type", "perm_code", "sort", "visible", "keep_alive", "is_ext",
)


def _perm_key(user_id: int) -> str:
    return _PERM_KEY.format(uid=user_id)


def _dump(payload: dict) -> dict:
    """把 ORM 菜单对象转成可 JSON 序列化的结构。"""
    data = dict(payload)
    data["menus"] = [
        {f: getattr(m, f, None) for f in _MENU_FIELDS} for m in payload.get("menus", [])
    ]
    return data


def _load(data: dict) -> dict:
    """反序列化：菜单还原成只读属性对象，调用方访问方式不变。"""
    payload = dict(data)
    payload["menus"] = [SimpleNamespace(**m) for m in data.get("menus", [])]
    return payload


# --------------------------------------------------------------------------- #
# 缓存
# --------------------------------------------------------------------------- #
async def invalidate_user(user_id: int) -> None:
    await cache.delete(_perm_key(user_id))


async def invalidate_tenant(tenant_id: int) -> None:
    """角色/授权/菜单变更时批量失效；tenant_id<=0 表示全量失效。"""
    if tenant_id <= 0:
        await cache.delete_prefix(_PERM_PREFIX)
        await cache.delete_prefix("rbac:perm:t:")
        return
    ids = await cache.get_json(_TENANT_KEY.format(tid=tenant_id)) or []
    if ids:
        await cache.delete(*[_perm_key(i) for i in ids])
    await cache.delete(_TENANT_KEY.format(tid=tenant_id))


async def _index_user(tenant_id: int, user_id: int) -> None:
    """把已缓存的用户登记到租户索引，供 invalidate_tenant 批量清理。"""
    key = _TENANT_KEY.format(tid=tenant_id)
    ids = await cache.get_json(key) or []
    if user_id not in ids:
        ids.append(user_id)
        await cache.set_json(key, ids, ttl=settings.CACHE_TTL * 2)


# --------------------------------------------------------------------------- #
# 权限聚合
# --------------------------------------------------------------------------- #
async def load_user_roles(db: AsyncSession, user: User) -> list[Role]:
    stmt = (
        select(Role)
        .join(Role.users)
        .where(User.id == user.id, Role.status == 1)
        .options(selectinload(Role.permissions), selectinload(Role.menus))
    )
    return list((await db.execute(stmt)).scalars().unique())


async def build_user_perm_payload(db: AsyncSession, user: User) -> dict:
    """返回 {permissions, roles, menus(扁平), data_scope, tenant_id}。"""
    cached = await cache.get_json(_perm_key(user.id))
    if cached:
        return _load(cached)

    if user.is_superuser:
        menus = list(
            (await db.execute(select(Menu).where(Menu.status == 1).order_by(Menu.sort))).scalars()
        )
        payload = {
            "tenant_id": user.tenant_id,
            "permissions": [SUPER_PERM],
            "roles": ["super_admin"],
            "menus": menus,
            "data_scope": 1,
        }
    else:
        roles = await load_user_roles(db, user)
        if any(r.is_all_perm for r in roles):
            # 全量权限角色：效果等同超管，但 roles 仍返回真实角色标识，便于前端展示与审计
            menus = list(
                (await db.execute(select(Menu).where(Menu.status == 1).order_by(Menu.sort))).scalars()
            )
            payload = {
                "tenant_id": user.tenant_id,
                "permissions": [SUPER_PERM],
                "roles": [r.code for r in roles],
                "menus": menus,
                "data_scope": 1,
            }
        else:
            perms: set[str] = set()
            menu_map: dict[int, Menu] = {}
            for r in roles:
                perms.update(p.code for p in r.permissions)
                for m in r.menus:
                    if m.status == 1:
                        menu_map[m.id] = m
            # 取最宽松的数据范围（数值越小范围越大）
            data_scope = min([r.data_scope for r in roles], default=1)
            payload = {
                "tenant_id": user.tenant_id,
                "permissions": sorted(perms),
                "roles": [r.code for r in roles],
                "menus": sorted(menu_map.values(), key=lambda m: m.sort),
                "data_scope": data_scope,
            }

    await cache.set_json(_perm_key(user.id), _dump(payload), ttl=settings.CACHE_TTL)
    await _index_user(user.tenant_id, user.id)
    return payload


def has_permission(perms: Iterable[str], required: Iterable[str], mode: str = "any") -> bool:
    perms = set(perms)
    if SUPER_PERM in perms:
        return True
    required = set(required)
    if not required:
        return True
    return required.issubset(perms) if mode == "all" else bool(perms & required)


# --------------------------------------------------------------------------- #
# 菜单树
# --------------------------------------------------------------------------- #
def build_menu_tree(menus: list[Menu], only_visible: bool = False,
                    parent_id: int = 0) -> list[dict]:
    """把扁平菜单列表构造成树，按钮类型不进入导航树。"""
    children_map: dict[int, list[Menu]] = {}
    for m in menus:
        children_map.setdefault(m.parent_id, []).append(m)

    def walk(pid: int) -> list[dict]:
        out: list[dict] = []
        for m in sorted(children_map.get(pid, []), key=lambda x: x.sort):
            if m.type == "button":
                continue
            if only_visible and not m.visible:
                continue
            node = {
                "id": m.id,
                "parent_id": m.parent_id,
                "title": m.title,
                "name": m.name,
                "path": m.path,
                "component": m.component,
                "icon": m.icon,
                "type": m.type,
                "perm_code": m.perm_code,
                "sort": m.sort,
                "visible": m.visible,
                "keep_alive": m.keep_alive,
                "is_ext": m.is_ext,
                "children": walk(m.id),
            }
            out.append(node)
        return out

    return walk(parent_id)


# --------------------------------------------------------------------------- #
# 数据范围
# --------------------------------------------------------------------------- #
async def resolve_dept_ids(db: AsyncSession, user: User, reason: dict) -> Optional[list[int]]:
    """返回 None 表示不限制；否则返回允许访问的部门 id 列表。"""
    if user.is_superuser or reason.get("data_scope") == 1:
        return None
    if user.dept_id is None:
        return []

    scope = reason.get("data_scope", 1)
    if scope == 4:  # 仅本人 -> 用 user_id 过滤，这里返回空部门列表交由调用方处理
        return []

    from app.models import Dept

    all_depts = list(
        (await db.execute(select(Dept).where(Dept.tenant_id == user.tenant_id))).scalars()
    )
    by_parent: dict[int, list[Dept]] = {}
    for d in all_depts:
        by_parent.setdefault(d.parent_id, []).append(d)

    if scope == 2:  # 本部门
        return [user.dept_id]

    def collect(root: int) -> list[int]:
        out = [root]
        for child in by_parent.get(root, []):
            out.extend(collect(child.id))
        return out

    if scope == 3:  # 本部门及以下
        return collect(user.dept_id)

    # scope == 5 自定义
    roles = await load_user_roles(db, user)
    custom: set[int] = set()
    for r in roles:
        if r.data_scope == 5:
            custom.update(r.custom_dept_ids or [])
    return sorted(custom)
