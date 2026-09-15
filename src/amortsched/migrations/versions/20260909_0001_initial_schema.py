"""Create the initial application schema.

Revision ID: 20260909_0001
Revises:
Create Date: 2026-09-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260909_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_table(
        "profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("locale", sa.String(), nullable=True),
        sa.Column("timezone", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_profiles_user_id"),
    )
    op.create_table(
        "plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("term_years", sa.Integer(), nullable=False),
        sa.Column("term_months", sa.Integer(), nullable=False),
        sa.Column("interest_rate", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("early_payment_fees", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("interest_rate_application", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("one_time_extra_payments", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("recurring_extra_payments", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("interest_rate_changes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_plans_amount_positive"),
        sa.CheckConstraint("interest_rate >= 0 AND interest_rate <= 100", name="ck_plans_interest_rate_range"),
        sa.CheckConstraint("term_years * 12 + term_months > 0", name="ck_plans_term_positive"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"], unique=False)
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)
    op.create_table(
        "schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("installments", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("totals", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("schedules")
    op.drop_index("ix_refresh_tokens_token_hash", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_family_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_table("plans")
    op.drop_table("profiles")
    op.drop_table("users")
