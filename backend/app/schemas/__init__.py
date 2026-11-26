"""Pydantic 模型（请求/响应）。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    msg: str = "ok"
    data: Optional[T] = None


class PageResult(BaseModel, Generic[T]):
    total: int = 0
    items: list[T] = Field(default_factory=list)


class PageQuery(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=200)
    keyword: Optional[str] = None


# --------------------------------------------------------------------------- #
# 认证
# --------------------------------------------------------------------------- #
class LoginIn(BaseModel):
    username: str
    password: str
    tenant_code: str = "platform"


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class RefreshIn(BaseModel):
    refresh_token: str


# --------------------------------------------------------------------------- #
# 权限
# --------------------------------------------------------------------------- #
class PermissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    module: str
    group: str
    sort: int = 0


class MenuOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    parent_id: int
    title: str
    name: str
    path: str
    component: str = ""
    icon: Optional[str] = None
    type: str = "menu"
    perm_code: Optional[str] = None
    sort: int = 0
    visible: bool = True
    keep_alive: bool = False
    is_ext: bool = False
    children: list["MenuOut"] = Field(default_factory=list)


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tenant_id: int
    code: str
    name: str
    data_scope: int
    custom_dept_ids: list[int] = Field(default_factory=list)
    status: int = 1
    is_system: bool = False
    is_all_perm: bool = False
    sort: int = 0
    remark: Optional[str] = None


class RoleBrief(BaseModel):
    """用户返回体中的角色摘要。"""

    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str


class RoleCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=64)
    data_scope: int = 1
    custom_dept_ids: list[int] = Field(default_factory=list)
    status: int = 1
    is_all_perm: bool = False
    sort: int = 0
    remark: Optional[str] = None


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    data_scope: Optional[int] = None
    custom_dept_ids: Optional[list[int]] = None
    status: Optional[int] = None
    is_all_perm: Optional[bool] = None
    sort: Optional[int] = None
    remark: Optional[str] = None


class RoleGrantIn(BaseModel):
    permission_ids: list[int] = Field(default_factory=list)
    menu_ids: list[int] = Field(default_factory=list)
    data_scope: Optional[int] = None
    is_all_perm: Optional[bool] = None


# --------------------------------------------------------------------------- #
# 用户
# --------------------------------------------------------------------------- #
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tenant_id: int
    dept_id: Optional[int] = None
    username: str
    nickname: str = ""
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None
    status: int = 1
    is_superuser: bool = False
    last_login_at: Optional[datetime] = None
    roles: list[RoleBrief] = Field(default_factory=list)


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str
    nickname: str = ""
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    dept_id: Optional[int] = None
    status: int = 1
    role_ids: list[int] = Field(default_factory=list)


class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    dept_id: Optional[int] = None
    status: Optional[int] = None
    role_ids: Optional[list[int]] = None


class PasswordResetIn(BaseModel):
    new_password: str


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str


# --------------------------------------------------------------------------- #
# 租户
# --------------------------------------------------------------------------- #
class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    contact: Optional[str] = None
    phone: Optional[str] = None
    status: int = 1
    max_users: int = 100
    expire_at: Optional[datetime] = None
    remark: Optional[str] = None


class TenantCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    contact: Optional[str] = None
    phone: Optional[str] = None
    max_users: int = 100
    expire_at: Optional[datetime] = None
    remark: Optional[str] = None


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[int] = None
    max_users: Optional[int] = None
    expire_at: Optional[datetime] = None
    remark: Optional[str] = None


# --------------------------------------------------------------------------- #
# 登录态聚合
# --------------------------------------------------------------------------- #
class ProfileOut(BaseModel):
    user: UserOut
    tenant: dict[str, Any] = Field(default_factory=dict)
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    menus: list[MenuOut] = Field(default_factory=list)
    data_scope: int = 1


# --------------------------------------------------------------------------- #
# 日志审计
# --------------------------------------------------------------------------- #
class LoginLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tenant_id: int
    user_id: Optional[int] = None
    username: str
    login_type: str
    status: int
    fail_reason: Optional[str] = None
    ip: str
    ip_region: Optional[str] = None
    os: Optional[str] = None
    browser: Optional[str] = None
    device: Optional[str] = None
    user_agent: Optional[str] = None
    login_at: Optional[datetime] = None


class OperationLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tenant_id: int
    user_id: Optional[int] = None
    username: Optional[str] = None
    module: str
    action: str
    action_label: str
    method: str
    path: str
    query: Optional[str] = None
    target: Optional[str] = None
    params: Optional[str] = None
    status_code: int
    success: bool
    error_msg: Optional[str] = None
    duration_ms: int
    ip: str
    ip_region: Optional[str] = None
    os: Optional[str] = None
    browser: Optional[str] = None
    device: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: Optional[datetime] = None


class LogCleanIn(BaseModel):
    """按时间清理日志：保留 before 之后的记录。"""
    before: datetime
