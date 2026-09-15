"""Add missing foreign key and soft delete indexes.

Revision ID: 20260910_0002
Revises: 20260909_0001
Create Date: 2026-09-10
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260910_0002"
down_revision: str | None = "20260909_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_plans_user_id", "plans", ["user_id"], unique=False)
    op.create_index("ix_plans_user_id_is_deleted", "plans", ["user_id", "is_deleted"], unique=False)
    op.create_index("ix_schedules_plan_id", "schedules", ["plan_id"], unique=False)
    op.create_index("ix_schedules_plan_id_is_deleted", "schedules", ["plan_id", "is_deleted"], unique=False)
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_index("ix_schedules_plan_id_is_deleted", table_name="schedules")
    op.drop_index("ix_schedules_plan_id", table_name="schedules")
    op.drop_index("ix_plans_user_id_is_deleted", table_name="plans")
    op.drop_index("ix_plans_user_id", table_name="plans")
