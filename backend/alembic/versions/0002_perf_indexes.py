"""外部数据库的复合索引

SQLite 单机场景下这些索引收益有限，故在 sqlite 方言上直接跳过；
MySQL/PostgreSQL 上租户维度查询是主要路径，按 (tenant_id, 时间/状态) 建复合索引。

Revision ID: 0002_perf_indexes
Revises: 0001_baseline
Create Date: 2026-11-26
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import inspect

revision = "0002_perf_indexes"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None

# (索引名, 表名, 列)
INDEXES: list[tuple[str, str, list[str]]] = [
    ("ix_sys_user_tenant_status", "sys_user", ["tenant_id", "status"]),
    ("ix_sys_role_tenant_status", "sys_role", ["tenant_id", "status"]),
    ("ix_sys_dept_tenant_parent", "sys_dept", ["tenant_id", "parent_id"]),
    ("ix_sys_menu_parent_sort", "sys_menu", ["parent_id", "sort"]),
    ("ix_sys_perm_module_code", "sys_permission", ["module", "code"]),
    ("ix_sys_login_log_tenant_time", "sys_login_log", ["tenant_id", "login_at"]),
    ("ix_sys_login_log_user_time", "sys_login_log", ["user_id", "login_at"]),
    ("ix_sys_oper_log_tenant_time", "sys_operation_log", ["tenant_id", "created_at"]),
    ("ix_sys_oper_log_user_time", "sys_operation_log", ["user_id", "created_at"]),
]


def _existing_indexes(bind: object, table: str) -> set[str]:
    """在线模式反射已有索引以保持幂等；offline（--sql）模式无法反射，直接按脚本输出。"""
    try:
        insp = inspect(bind)
        return {i["name"] for i in insp.get_indexes(table)}
    except Exception:
        return set()


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return
    for name, table, cols in INDEXES:
        if name in _existing_indexes(bind, table):
            continue
        op.create_index(name, table, cols)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return
    for name, table, _ in INDEXES:
        op.drop_index(name, table_name=table)
