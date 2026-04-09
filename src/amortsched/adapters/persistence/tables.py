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
    Column("password_hash", sqlalchemy.String, nullable=False),
    Column("created_at", sqlalchemy.DateTime(timezone=True), nullable=False),
    Column("updated_at", sqlalchemy.DateTime(timezone=True), nullable=False),
    sqlalchemy.UniqueConstraint("email", name="uq_users_email"),
)

profiles = sqlalchemy.Table(
    "profiles",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("user_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("users.id"), nullable=False),
    Column("display_name", sqlalchemy.String, nullable=True),
    Column("phone", sqlalchemy.String, nullable=True),
    Column("locale", sqlalchemy.String, nullable=True),
    Column("timezone", sqlalchemy.String, nullable=True),
    Column("created_at", sqlalchemy.DateTime(timezone=True), nullable=False),
    Column("updated_at", sqlalchemy.DateTime(timezone=True), nullable=False),
    sqlalchemy.UniqueConstraint("user_id", name="uq_profiles_user_id"),
)

plans = sqlalchemy.Table(
    "plans",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("user_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("users.id"), nullable=False),
    Column("name", sqlalchemy.String, nullable=False),
    Column("slug", sqlalchemy.String, nullable=False),
    Column("amount", sqlalchemy.Numeric(precision=18, scale=2), nullable=False),
    Column("term_years", sqlalchemy.Integer, nullable=False),
    Column("term_months", sqlalchemy.Integer, nullable=False),
    Column("interest_rate", sqlalchemy.Numeric(precision=9, scale=6), nullable=False),
    Column("start_date", sqlalchemy.Date, nullable=False),
    Column("early_payment_fees", JSONB, nullable=False),
    Column("interest_rate_application", sqlalchemy.String, nullable=False),
    Column("status", sqlalchemy.String, nullable=False),
    Column("one_time_extra_payments", JSONB, nullable=False),
    Column("recurring_extra_payments", JSONB, nullable=False),
    Column("interest_rate_changes", JSONB, nullable=False),
    Column("is_deleted", sqlalchemy.Boolean, nullable=False),
    Column("created_at", sqlalchemy.DateTime(timezone=True), nullable=False),
    Column("updated_at", sqlalchemy.DateTime(timezone=True), nullable=False),
)

schedules = sqlalchemy.Table(
    "schedules",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("plan_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("plans.id"), nullable=False),
    Column("installments", JSONB, nullable=False),
    Column("totals", JSONB, nullable=True),
    Column("generated_at", sqlalchemy.DateTime(timezone=True), nullable=False),
    Column("is_deleted", sqlalchemy.Boolean, nullable=False),
)

refresh_tokens = sqlalchemy.Table(
    "refresh_tokens",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("user_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("token_hash", sqlalchemy.String(128), nullable=False, unique=True, index=True),
    Column("family_id", UUID(as_uuid=True), nullable=False, index=True),
    Column("expires_at", sqlalchemy.DateTime(timezone=True), nullable=False),
    Column("used_at", sqlalchemy.DateTime(timezone=True), nullable=True),
    Column("revoked_at", sqlalchemy.DateTime(timezone=True), nullable=True),
    Column("created_at", sqlalchemy.DateTime(timezone=True), nullable=False, server_default=sqlalchemy.func.now()),
)
