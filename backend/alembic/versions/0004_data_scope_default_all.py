"""sys_role.data_scope 默认与既有数据统一为「全部数据」

Revision ID: 0004_data_scope_default_all
Revises: 0003_role_all_perm
Create Date: 2026-11-26

说明：平台侧不再通过 data_scope 做行级裁剪，默认值由 4（仅本人）改为 1（全部数据），
并把历史数据中残留的 4（仅本人）一并纠正为 1，避免存量角色仍只能看到自己创建的记录。
2/3/5 属于显式的部门级授权，保持原值不动。
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_data_scope_default_all"
down_revision = "0003_role_all_perm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # 存量数据纠正：仅本人 -> 全部数据
    bind.execute(sa.text("UPDATE sys_role SET data_scope = 1 WHERE data_scope = 4"))
    # 列默认值（数据库支持时设置，不支持则忽略）
    try:
        with op.batch_alter_table("sys_role") as batch:
            batch.alter_column(
                "data_scope",
                existing_type=sa.Integer(),
                server_default=sa.text("1"),
                existing_nullable=False,
            )
    except Exception:
        pass


def downgrade() -> None:
    bind = op.get_bind()
    try:
        with op.batch_alter_table("sys_role") as batch:
            batch.alter_column(
                "data_scope",
                existing_type=sa.Integer(),
                server_default=None,
                existing_nullable=False,
            )
    except Exception:
        pass
    bind.execute(sa.text("UPDATE sys_role SET data_scope = 4 WHERE data_scope = 1 AND code = 'viewer'"))
