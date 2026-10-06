"""Add loan type, currency, and housing costs to plans.

Revision ID: 20261006_0005
Revises: 20261006_0004
Create Date: 2026-10-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261006_0005"
down_revision: str | None = "20261006_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("plans", sa.Column("loan_type", sa.String(length=32), server_default="other", nullable=False))
    op.add_column("plans", sa.Column("currency", sa.String(length=3), server_default="USD", nullable=False))
    op.add_column(
        "plans",
        sa.Column("housing_costs", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("plans", "housing_costs")
    op.drop_column("plans", "currency")
    op.drop_column("plans", "loan_type")
