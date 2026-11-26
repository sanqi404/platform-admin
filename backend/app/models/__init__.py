"""全部 ORM 模型。

- tenant_id 冗余在每张业务表，查询层强制过滤，避免跨租户越权；
- permission 为权限点字典（模块:资源:动作），与 menu 解耦；
- menu.perm_code 引用 permission.code，供前端做菜单/按钮显隐；
- role 同时关联 permission（功能权限）与 menu（菜单权限），
  并携带 data_scope（数据范围）用于行级过滤。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, JSON,
    String, Table, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

# SQLite 只对 INTEGER PRIMARY KEY 自增，BigInteger 主键会导致 NOT NULL 失败；
# 因此用 variant 在其他数据库保持 BIGINT，在 SQLite 上降级为 INTEGER。
ID_TYPE = BigInteger().with_variant(Integer, "sqlite")

# --------------------------------------------------------------------------- #
# 关联表
# --------------------------------------------------------------------------- #
user_role = Table(
    "sys_user_role", Base.metadata,
    Column("user_id", ID_TYPE, ForeignKey("sys_user.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ID_TYPE, ForeignKey("sys_role.id", ondelete="CASCADE"), primary_key=True),
)

role_permission = Table(
    "sys_role_permission", Base.metadata,
    Column("role_id", ID_TYPE, ForeignKey("sys_role.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", ID_TYPE, ForeignKey("sys_permission.id", ondelete="CASCADE"), primary_key=True),
)

role_menu = Table(
    "sys_role_menu", Base.metadata,
    Column("role_id", ID_TYPE, ForeignKey("sys_role.id", ondelete="CASCADE"), primary_key=True),
    Column("menu_id", ID_TYPE, ForeignKey("sys_menu.id", ondelete="CASCADE"), primary_key=True),
)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


# --------------------------------------------------------------------------- #
# 租户
# --------------------------------------------------------------------------- #
class Tenant(Base, TimestampMixin):
    __tablename__ = "sys_tenant"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment="租户编码")
    name: Mapped[str] = mapped_column(String(128), comment="租户名称")
    contact: Mapped[Optional[str]] = mapped_column(String(64), default=None)
    phone: Mapped[Optional[str]] = mapped_column(String(32), default=None)
    status: Mapped[int] = mapped_column(Integer, default=1, comment="1启用 0停用")
    max_users: Mapped[int] = mapped_column(Integer, default=100)
    expire_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    remark: Mapped[Optional[str]] = mapped_column(String(255), default=None)

    users: Mapped[list["User"]] = relationship(back_populates="tenant")


# --------------------------------------------------------------------------- #
# 部门
# --------------------------------------------------------------------------- #
class Dept(Base, TimestampMixin):
    __tablename__ = "sys_dept"
    __table_args__ = (UniqueConstraint("tenant_id", "name", "parent_id", name="uq_dept_tenant_name"),)

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ID_TYPE, index=True)
    parent_id: Mapped[int] = mapped_column(ID_TYPE, default=0, index=True)
    name: Mapped[str] = mapped_column(String(64))
    leader: Mapped[Optional[str]] = mapped_column(String(64), default=None)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[int] = mapped_column(Integer, default=1)


# --------------------------------------------------------------------------- #
# 用户
# --------------------------------------------------------------------------- #
class User(Base, TimestampMixin):
    __tablename__ = "sys_user"
    __table_args__ = (UniqueConstraint("tenant_id", "username", name="uq_user_tenant_username"),)

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        ID_TYPE, ForeignKey("sys_tenant.id", ondelete="CASCADE"), index=True
    )
    dept_id: Mapped[Optional[int]] = mapped_column(
        ID_TYPE, ForeignKey("sys_dept.id", ondelete="SET NULL"), default=None, index=True
    )
    username: Mapped[str] = mapped_column(String(64), index=True)
    nickname: Mapped[str] = mapped_column(String(64), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(128), default=None)
    phone: Mapped[Optional[str]] = mapped_column(String(32), default=None)
    avatar: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    status: Mapped[int] = mapped_column(Integer, default=1, comment="1启用 0停用")
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, comment="超管绕过权限校验")
    login_fail_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    last_login_ip: Mapped[Optional[str]] = mapped_column(String(64), default=None)

    tenant: Mapped["Tenant"] = relationship(back_populates="users", lazy="selectin")
    roles: Mapped[list["Role"]] = relationship(secondary=user_role, lazy="selectin", back_populates="users")


# --------------------------------------------------------------------------- #
# 角色
# --------------------------------------------------------------------------- #
class Role(Base, TimestampMixin):
    __tablename__ = "sys_role"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_role_tenant_code"),)

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        ID_TYPE, ForeignKey("sys_tenant.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(64), comment="角色标识，前端 v-role 使用")
    name: Mapped[str] = mapped_column(String(64))
    data_scope: Mapped[int] = mapped_column(Integer, default=1, comment="1全部 2本部门 3本部及以下 4仅本人 5自定义")
    custom_dept_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    status: Mapped[int] = mapped_column(Integer, default=1)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, comment="内置角色不可删除")
    is_all_perm: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="全量权限：忽略绑定直接拥有租户内全部权限点与菜单"
    )
    sort: Mapped[int] = mapped_column(Integer, default=0)
    remark: Mapped[Optional[str]] = mapped_column(String(255), default=None)

    users: Mapped[list["User"]] = relationship(secondary=user_role, back_populates="roles")
    permissions: Mapped[list["Permission"]] = relationship(secondary=role_permission, lazy="selectin")
    menus: Mapped[list["Menu"]] = relationship(secondary=role_menu, lazy="selectin")


# --------------------------------------------------------------------------- #
# 权限点字典
# --------------------------------------------------------------------------- #
class Permission(Base, TimestampMixin):
    __tablename__ = "sys_permission"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(128), unique=True, index=True,
                                      comment="权限码 模块:资源:动作")
    name: Mapped[str] = mapped_column(String(64))
    module: Mapped[str] = mapped_column(String(64), index=True, comment="所属模块")
    group: Mapped[str] = mapped_column(String(64), default="默认", comment="UI 分组")
    sort: Mapped[int] = mapped_column(Integer, default=0)
    remark: Mapped[Optional[str]] = mapped_column(String(255), default=None)


# --------------------------------------------------------------------------- #
# 菜单
# --------------------------------------------------------------------------- #
class Menu(Base, TimestampMixin):
    __tablename__ = "sys_menu"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    parent_id: Mapped[int] = mapped_column(ID_TYPE, default=0, index=True)
    title: Mapped[str] = mapped_column(String(64), comment="菜单标题")
    name: Mapped[str] = mapped_column(String(64), comment="路由 name，唯一")
    path: Mapped[str] = mapped_column(String(128), default="", comment="路由 path")
    component: Mapped[str] = mapped_column(String(128), default="", comment="组件路径，如 system/user/index")
    icon: Mapped[Optional[str]] = mapped_column(String(64), default=None)
    type: Mapped[str] = mapped_column(String(16), default="menu", comment="dir 目录 / menu 菜单 / button 按钮")
    perm_code: Mapped[Optional[str]] = mapped_column(String(128), default=None, comment="绑定权限码")
    sort: Mapped[int] = mapped_column(Integer, default=0)
    visible: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否在侧边栏显示")
    keep_alive: Mapped[bool] = mapped_column(Boolean, default=False)
    is_ext: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否外链")
    status: Mapped[int] = mapped_column(Integer, default=1)


# --------------------------------------------------------------------------- #
# 登录日志
# --------------------------------------------------------------------------- #
class LoginLog(Base):
    __tablename__ = "sys_login_log"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ID_TYPE, default=0, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ID_TYPE, default=None, index=True,
                                                   comment="登录成功/失败已识别用户时写入，用户不存在则空")
    username: Mapped[str] = mapped_column(String(64), index=True, comment="提交的登录账号")
    login_type: Mapped[str] = mapped_column(String(16), default="login",
                                            comment="login 登录 / logout 登出 / refresh 刷新令牌")
    status: Mapped[int] = mapped_column(Integer, default=1, index=True, comment="1成功 0失败")
    fail_reason: Mapped[Optional[str]] = mapped_column(String(255), default=None)

    ip: Mapped[str] = mapped_column(String(64), default="unknown", index=True)
    ip_region: Mapped[Optional[str]] = mapped_column(String(32), default=None, comment="本机/内网/公网")
    user_agent: Mapped[Optional[str]] = mapped_column(Text, default=None)
    os: Mapped[Optional[str]] = mapped_column(String(64), default=None)
    browser: Mapped[Optional[str]] = mapped_column(String(64), default=None)
    device: Mapped[Optional[str]] = mapped_column(String(32), default=None, comment="PC/移动端/程序调用")

    login_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


# --------------------------------------------------------------------------- #
# 操作日志
# --------------------------------------------------------------------------- #
class OperationLog(Base):
    __tablename__ = "sys_operation_log"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ID_TYPE, default=0, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ID_TYPE, default=None, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), default=None, index=True)

    module: Mapped[str] = mapped_column(String(64), default="系统", index=True, comment="业务模块")
    action: Mapped[str] = mapped_column(String(32), default="other", index=True,
                                        comment="create/update/delete/grant/export/reset_password/other")
    action_label: Mapped[str] = mapped_column(String(64), default="", comment="人可读动作，如「新增用户管理」")
    method: Mapped[str] = mapped_column(String(8), default="")
    path: Mapped[str] = mapped_column(String(255), default="", index=True)
    query: Mapped[Optional[str]] = mapped_column(String(512), default=None, comment="查询串")
    target: Mapped[Optional[str]] = mapped_column(String(255), default=None, comment="操作对象，如 users #3")
    params: Mapped[Optional[str]] = mapped_column(Text, default=None, comment="请求体，已脱敏截断")

    status_code: Mapped[int] = mapped_column(Integer, default=0, index=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    error_msg: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)

    ip: Mapped[str] = mapped_column(String(64), default="unknown", index=True)
    ip_region: Mapped[Optional[str]] = mapped_column(String(32), default=None)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, default=None)
    os: Mapped[Optional[str]] = mapped_column(String(64), default=None)
    browser: Mapped[Optional[str]] = mapped_column(String(64), default=None)
    device: Mapped[Optional[str]] = mapped_column(String(32), default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
