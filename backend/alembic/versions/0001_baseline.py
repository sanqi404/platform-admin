"""baseline：初始表结构与种子表

直接以 ORM metadata 建表，保证 DDL 与模型完全一致（含 BigInteger/Integer 的
方言 variant、外键、唯一约束），避免手写 DDL 与模型漂移。

Revision ID: 0001_baseline
Revises:
Create Date: 2026-11-26
"""
from __future__ import annotations

from alembic import op

from app import models  # noqa: F401  注册全部模型
from app.db.session import Base

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
