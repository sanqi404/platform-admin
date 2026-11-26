"""种子数据：权限点字典、菜单树、内置角色、初始管理员。

重复执行不会写入重复数据。
"""
from __future__ import annotations

from sqlalchemy import delete, inspect as sa_inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models import Menu, Permission, Role, Tenant, User, role_menu

# --------------------------------------------------------------------------- #
# 权限点字典：模块:资源:动作
# --------------------------------------------------------------------------- #
PERMISSIONS: list[tuple[str, str, str, str]] = [
    # (code, name, module, group)
    ("dashboard:view", "查看工作台", "dashboard", "工作台"),
    ("system:user:list", "用户查询", "user", "用户管理"),
    ("system:user:create", "用户新增", "user", "用户管理"),
    ("system:user:update", "用户编辑", "user", "用户管理"),
    ("system:user:delete", "用户删除", "user", "用户管理"),
    ("system:user:resetPwd", "重置密码", "user", "用户管理"),
    ("system:role:list", "角色查询", "role", "角色管理"),
    ("system:role:create", "角色新增", "role", "角色管理"),
    ("system:role:update", "角色编辑", "role", "角色管理"),
    ("system:role:delete", "角色删除", "role", "角色管理"),
    ("system:role:grant", "角色授权", "role", "角色管理"),
    ("system:menu:list", "菜单查询", "menu", "菜单管理"),
    ("system:menu:create", "菜单新增", "menu", "菜单管理"),
    ("system:menu:update", "菜单编辑", "menu", "菜单管理"),
    ("system:menu:delete", "菜单删除", "menu", "菜单管理"),
    ("system:tenant:list", "租户查询", "tenant", "租户管理"),
    ("system:tenant:create", "租户新增", "tenant", "租户管理"),
    ("system:tenant:update", "租户编辑", "tenant", "租户管理"),
    ("system:tenant:delete", "租户删除", "tenant", "租户管理"),
    ("system:loginlog:list", "登录日志查询", "loginlog", "日志审计"),
    ("system:loginlog:delete", "登录日志清理", "loginlog", "日志审计"),
    ("system:operlog:list", "操作日志查询", "operlog", "日志审计"),
    ("system:operlog:delete", "操作日志清理", "operlog", "日志审计"),
]

# --------------------------------------------------------------------------- #
# 菜单树：(title, name, path, component, icon, type, perm_code, children)
# --------------------------------------------------------------------------- #
MENUS = [
    ("工作台", "Dashboard", "/dashboard", "dashboard/index", "Odometer", "menu", "dashboard:view", []),
    ("系统管理", "System", "/system", "", "Setting", "dir", None, [
        ("用户管理", "SystemUser", "/system/user", "system/user/index", "User", "menu",
         "system:user:list", [
             ("新增用户", "SystemUserCreate", "", "", None, "button", "system:user:create", []),
             ("编辑用户", "SystemUserUpdate", "", "", None, "button", "system:user:update", []),
             ("删除用户", "SystemUserDelete", "", "", None, "button", "system:user:delete", []),
             ("重置密码", "SystemUserResetPwd", "", "", None, "button", "system:user:resetPwd", []),
         ]),
        ("角色权限", "SystemRole", "/system/role", "system/role/index", "UserFilled", "menu",
         "system:role:list", [
             ("新增角色", "SystemRoleCreate", "", "", None, "button", "system:role:create", []),
             ("编辑角色", "SystemRoleUpdate", "", "", None, "button", "system:role:update", []),
             ("删除角色", "SystemRoleDelete", "", "", None, "button", "system:role:delete", []),
             ("分配权限", "SystemRoleGrant", "", "", None, "button", "system:role:grant", []),
         ]),
        ("菜单管理", "SystemMenu", "/system/menu", "system/menu/index", "Menu", "menu",
         "system:menu:list", [
             ("新增菜单", "SystemMenuCreate", "", "", None, "button", "system:menu:create", []),
             ("编辑菜单", "SystemMenuUpdate", "", "", None, "button", "system:menu:update", []),
             ("删除菜单", "SystemMenuDelete", "", "", None, "button", "system:menu:delete", []),
         ]),
        ("租户管理", "SystemTenant", "/system/tenant", "system/tenant/index", "OfficeBuilding", "menu",
         "system:tenant:list", [
             ("新增租户", "SystemTenantCreate", "", "", None, "button", "system:tenant:create", []),
             ("编辑租户", "SystemTenantUpdate", "", "", None, "button", "system:tenant:update", []),
             ("删除租户", "SystemTenantDelete", "", "", None, "button", "system:tenant:delete", []),
         ]),
        ("登录日志", "SystemLoginLog", "/system/login-log", "system/login-log/index", "Tickets", "menu",
         "system:loginlog:list", [
             ("清理登录日志", "SystemLoginLogDelete", "", "", None, "button", "system:loginlog:delete", []),
         ]),
        ("操作日志", "SystemOperLog", "/system/operation-log", "system/operation-log/index", "Document", "menu",
         "system:operlog:list", [
             ("清理操作日志", "SystemOperLogDelete", "", "", None, "button", "system:operlog:delete", []),
         ]),
    ]),
]



async def _purge_demo_menu(db: AsyncSession) -> None:
    """移除早期版本下发的「权限演示」菜单及其角色关联，可重复执行。"""
    rows = list((await db.execute(
        select(Menu).where(Menu.name.like("PermissionDemo%"))
    )).scalars())
    if not rows:
        return
    ids = [m.id for m in rows]
    await db.execute(delete(role_menu).where(role_menu.c.menu_id.in_(ids)))
    await db.execute(delete(Menu).where(Menu.id.in_(ids)))
    await db.flush()


async def _ensure_loaded(db: AsyncSession, obj, names: list[str]) -> None:
    """对已持久化对象的关联集合做显式加载，避免赋值时触发同步 lazy load
    （异步 session 下会抛 MissingGreenlet）。"""
    if sa_inspect(obj).persistent:
        await db.refresh(obj, attribute_names=names)


async def _seed_menus(db: AsyncSession, tenant_id: int) -> list[Menu]:
    created: list[Menu] = []

    async def walk(nodes, parent_id: int, parent_name: str = ""):
        for idx, (title, name, path, component, icon, mtype, code, children) in enumerate(nodes):
            unique_name = name if parent_id == 0 else f"{parent_name}.{name}"
            exists = (await db.execute(select(Menu).where(Menu.name == unique_name))).scalar_one_or_none()
            if exists is None:
                exists = Menu(title=title, name=unique_name, path=path, component=component,
                              icon=icon, type=mtype, perm_code=code, parent_id=parent_id,
                              sort=idx * 10, visible=True)
                db.add(exists)
                await db.flush()
            created.append(exists)
            if children:
                await walk(children, exists.id, unique_name)

    await walk(MENUS, 0)
    return created


async def create_tables() -> None:
    """按模型建表（开发/首装用；生产改用 alembic upgrade head）。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed(create: bool = True) -> None:
    """写入种子数据，重复执行不会写入重复行。create=True 时顺带建表。"""
    if create:
        await create_tables()

    async with SessionLocal() as db:
        # ---- 权限点 ----
        perm_map: dict[str, Permission] = {}
        for i, (code, name, module, group) in enumerate(PERMISSIONS):
            p = (await db.execute(select(Permission).where(Permission.code == code))).scalar_one_or_none()
            if p is None:
                p = Permission(code=code, name=name, module=module, group=group, sort=i)
                db.add(p)
            perm_map[code] = p
        await db.flush()

        # ---- 租户 ----
        tenant = (await db.execute(
            select(Tenant).where(Tenant.code == settings.INIT_TENANT_CODE)
        )).scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(code=settings.INIT_TENANT_CODE, name="平台运营中心",
                            contact="管理员", status=1, max_users=9999)
            db.add(tenant)
            await db.flush()
        tenant_id = tenant.id

        # ---- 菜单 ----
        await _purge_demo_menu(db)
        menus = await _seed_menus(db, tenant_id)

        # ---- 角色 ----
        admin_role = (await db.execute(
            select(Role).where(Role.tenant_id == tenant_id, Role.code == "super_admin")
        )).scalar_one_or_none()
        if admin_role is None:
            admin_role = Role(tenant_id=tenant_id, code="super_admin", name="超级管理员",
                              data_scope=1, is_system=True, sort=1)
            db.add(admin_role)
        await _ensure_loaded(db, admin_role, ["permissions", "menus"])
        # 内置超管角色标记为全量权限：后续新增权限点无需手工重新授权
        admin_role.is_all_perm = True
        admin_role.permissions = list(perm_map.values())
        admin_role.menus = menus

        viewer_role = (await db.execute(
            select(Role).where(Role.tenant_id == tenant_id, Role.code == "viewer")
        )).scalar_one_or_none()
        if viewer_role is None:
            viewer_role = Role(tenant_id=tenant_id, code="viewer", name="只读观察员",
                               data_scope=1, is_system=True, sort=2,
                               remark="仅可查看，用于演示权限差异")
            db.add(viewer_role)
        await _ensure_loaded(db, viewer_role, ["permissions", "menus"])
        viewer_role.permissions = [perm_map["dashboard:view"], perm_map["system:user:list"]]
        viewer_role.menus = [m for m in menus if m.name in (
            "Dashboard", "System", "System.SystemUser")]

        # ---- 管理员 ----
        admin = (await db.execute(
            select(User).where(User.tenant_id == tenant_id,
                               User.username == settings.INIT_ADMIN_USERNAME)
        )).scalar_one_or_none()
        if admin is None:
            admin = User(
                tenant_id=tenant_id,
                username=settings.INIT_ADMIN_USERNAME,
                nickname="平台管理员",
                password_hash=hash_password(settings.INIT_ADMIN_PASSWORD),
                is_superuser=True,
                status=1,
            )
            db.add(admin)
            await db.flush()
        await _ensure_loaded(db, admin, ["roles"])
        admin.roles = [admin_role]

        await db.commit()
        print("=" * 58)
        print(" 初始化完成")
        print(f" 租户编码: {settings.INIT_TENANT_CODE}")
        print(f" 登录账号: {settings.INIT_ADMIN_USERNAME} / {settings.INIT_ADMIN_PASSWORD}")
        print("=" * 58)


if __name__ == "__main__":
    import asyncio
    asyncio.run(seed())
