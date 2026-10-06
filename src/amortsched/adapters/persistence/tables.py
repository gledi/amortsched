import sqlalchemy
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.schema import Column

metadata = sqlalchemy.MetaData()

users = sqlalchemy.Table(
    "users",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("email", sqlalchemy.String, nullable=False),
    Column("name", sqlalchemy.String, nullable=False),
    Column("is_active", sqlalchemy.Boolean, nullable=False),
    Column("email_verified_at", sqlalchemy.DateTime(timezone=True), nullable=True),
    Column("password_hash", sqlalchemy.String, nullable=False),
    Column("created_at", sqlalchemy.DateTime(timezone=True), nullable=False),
    Column("updated_at", sqlalchemy.DateTime(timezone=True), nullable=False),
    sqlalchemy.UniqueConstraint("email", name="uq_users_email"),
)

profiles = sqlalchemy.Table(
    "profiles",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("user_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("display_name", sqlalchemy.String, nullable=True),
    Column("phone", sqlalchemy.String, nullable=True),
    Column("locale", sqlalchemy.String, nullable=True),
    Column("timezone", sqlalchemy.String, nullable=True),
    Column("currency", sqlalchemy.String(3), nullable=True),
    Column("created_at", sqlalchemy.DateTime(timezone=True), nullable=False),
    Column("updated_at", sqlalchemy.DateTime(timezone=True), nullable=False),
    sqlalchemy.UniqueConstraint("user_id", name="uq_profiles_user_id"),
)

plans = sqlalchemy.Table(
    "plans",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("user_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("name", sqlalchemy.String, nullable=False),
    Column("slug", sqlalchemy.String, nullable=False),
    Column("amount", sqlalchemy.Numeric(precision=18, scale=2), nullable=False),
    Column("term_years", sqlalchemy.Integer, nullable=False),
    Column("term_months", sqlalchemy.Integer, nullable=False),
    Column("interest_rate", sqlalchemy.Numeric(precision=9, scale=6), nullable=False),
    Column("start_date", sqlalchemy.Date, nullable=False),
    Column("loan_type", sqlalchemy.String(32), nullable=False, server_default=sqlalchemy.text("'other'")),
    Column("currency", sqlalchemy.String(3), nullable=False, server_default=sqlalchemy.text("'USD'")),
    Column("lender", sqlalchemy.String(200), nullable=True),
    Column(
        "upfront_fees",
        sqlalchemy.Numeric(precision=18, scale=2),
        nullable=False,
        server_default=sqlalchemy.text("0.00"),
    ),
    Column("early_payment_fees", JSONB, nullable=False),
    Column("housing_costs", JSONB, nullable=False, server_default=sqlalchemy.text("'{}'::jsonb")),
    Column("interest_rate_application", sqlalchemy.String, nullable=False),
    Column("status", sqlalchemy.String, nullable=False),
    Column("one_time_extra_payments", JSONB, nullable=False),
    Column("recurring_extra_payments", JSONB, nullable=False),
    Column("interest_rate_changes", JSONB, nullable=False),
    Column("is_deleted", sqlalchemy.Boolean, nullable=False),
    Column("created_at", sqlalchemy.DateTime(timezone=True), nullable=False),
    Column("updated_at", sqlalchemy.DateTime(timezone=True), nullable=False),
    sqlalchemy.CheckConstraint("amount > 0", name="ck_plans_amount_positive"),
    sqlalchemy.CheckConstraint("term_years * 12 + term_months > 0", name="ck_plans_term_positive"),
    sqlalchemy.CheckConstraint("interest_rate >= 0 AND interest_rate <= 100", name="ck_plans_interest_rate_range"),
    sqlalchemy.CheckConstraint("upfront_fees >= 0", name="ck_plans_upfront_fees_non_negative"),
    sqlalchemy.Index("ix_plans_user_id", "user_id"),
    sqlalchemy.Index("ix_plans_user_id_is_deleted", "user_id", "is_deleted"),
)

schedules = sqlalchemy.Table(
    "schedules",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("plan_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("plans.id", ondelete="CASCADE"), nullable=False),
    Column("installments", JSONB, nullable=False),
    Column("totals", JSONB, nullable=True),
    Column("generated_at", sqlalchemy.DateTime(timezone=True), nullable=False),
    Column("is_deleted", sqlalchemy.Boolean, nullable=False),
    sqlalchemy.Index("ix_schedules_plan_id", "plan_id"),
    sqlalchemy.Index("ix_schedules_plan_id_is_deleted", "plan_id", "is_deleted"),
)

refresh_tokens = sqlalchemy.Table(
    "refresh_tokens",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column(
        "user_id",
        UUID(as_uuid=True),
        sqlalchemy.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("token_hash", sqlalchemy.String(128), nullable=False, unique=True, index=True),
    Column("family_id", UUID(as_uuid=True), nullable=False, index=True),
    Column("expires_at", sqlalchemy.DateTime(timezone=True), nullable=False),
    Column("used_at", sqlalchemy.DateTime(timezone=True), nullable=True),
    Column("revoked_at", sqlalchemy.DateTime(timezone=True), nullable=True),
    Column("created_at", sqlalchemy.DateTime(timezone=True), nullable=False, server_default=sqlalchemy.func.now()),
)

account_tokens = sqlalchemy.Table(
    "account_tokens",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column(
        "user_id",
        UUID(as_uuid=True),
        sqlalchemy.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("purpose", sqlalchemy.String(32), nullable=False),
    Column("token_hash", sqlalchemy.String(128), nullable=False, unique=True, index=True),
    Column("expires_at", sqlalchemy.DateTime(timezone=True), nullable=False),
    Column("used_at", sqlalchemy.DateTime(timezone=True), nullable=True),
    Column("created_at", sqlalchemy.DateTime(timezone=True), nullable=False),
)
