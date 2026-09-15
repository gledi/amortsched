"""Add lender and upfront fees to plans.

Revision ID: 20260915_0003
Revises: 20260910_0002
Create Date: 2026-09-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260915_0003"
down_revision: str | None = "20260910_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("plans", sa.Column("lender", sa.String(length=200), nullable=True))
    op.add_column(
        "plans",
        sa.Column("upfront_fees", sa.Numeric(precision=18, scale=2), server_default="0.00", nullable=False),
    )
    op.create_check_constraint("ck_plans_upfront_fees_non_negative", "plans", "upfront_fees >= 0")


def downgrade() -> None:
    op.drop_constraint("ck_plans_upfront_fees_non_negative", "plans", type_="check")
    op.drop_column("plans", "upfront_fees")
    op.drop_column("plans", "lender")
