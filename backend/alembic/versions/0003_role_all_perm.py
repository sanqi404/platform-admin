"""sys_role 增加 is_all_perm 全量权限标记

Revision ID: 0003_role_all_perm
Revises: 0002_perf_indexes
Create Date: 2026-11-26

说明：is_all_perm=True 的角色忽略权限点/菜单绑定，直接拥有租户内全部权限点与菜单，
效果等同超管，但仍保留真实角色标识用于展示与审计。
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_role_all_perm"
down_revision = "0002_perf_indexes"
branch_labels = None
depends_on = None


def _has_column(bind, table: str, column: str) -> bool:
    try:
        return column in {c["name"] for c in sa.inspect(bind).get_columns(table)}
    except Exception:
        return False


def upgrade() -> None:
    bind = op.get_bind()
    if _has_column(bind, "sys_role", "is_all_perm"):
        return
    with op.batch_alter_table("sys_role") as batch:
        batch.add_column(sa.Column(
            "is_all_perm", sa.Boolean(), nullable=False,
            server_default=sa.false(), comment="全量权限：忽略绑定直接拥有全部权限点与菜单",
        ))


def downgrade() -> None:
    bind = op.get_bind()
    if not _has_column(bind, "sys_role", "is_all_perm"):
        return
    with op.batch_alter_table("sys_role") as batch:
        batch.drop_column("is_all_perm")
