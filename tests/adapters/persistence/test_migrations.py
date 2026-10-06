from decimal import Decimal

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError


def test_initial_migration_builds_schema(postgres, monkeypatch):
    database_url = postgres.get_connection_url(driver="psycopg")
    monkeypatch.setenv("DATABASE__DSN", database_url)
    config = Config("alembic.ini")

    command.upgrade(config, "20260910_0002")

    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text("""
                INSERT INTO users VALUES (
                    '00000000-0000-0000-0000-000000000001', 'migration@example.com', 'Existing owner',
                    true, 'hash', now(), now()
                )
            """)
            )
            connection.execute(
                text("""
                INSERT INTO plans (
                    id, user_id, name, slug, amount, term_years, term_months, interest_rate, start_date,
                    early_payment_fees, interest_rate_application, status, one_time_extra_payments,
                    recurring_extra_payments, interest_rate_changes, is_deleted, created_at, updated_at
                ) VALUES (
                    '00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000001',
                    'Existing plan', 'existing-plan', 1200, 1, 0, 3, '2026-01-01',
                    '{}', 'whole_month', 'draft', '[]', '[]', '[]', false, now(), now()
                )
            """)
            )
        command.upgrade(config, "head")
        inspector = inspect(engine)
        assert {
            "alembic_version",
            "users",
            "profiles",
            "plans",
            "schedules",
            "refresh_tokens",
            "account_tokens",
        } <= set(inspector.get_table_names())
        user_columns = {column["name"]: column for column in inspector.get_columns("users")}
        assert user_columns["email_verified_at"]["nullable"] is True
        profile_columns = {column["name"] for column in inspector.get_columns("profiles")}
        assert "currency" in profile_columns
        token_indexes = {index["name"]: index for index in inspector.get_indexes("account_tokens")}
        assert token_indexes["ix_account_tokens_token_hash"]["unique"]
        columns = {column["name"]: column for column in inspector.get_columns("plans")}
        assert columns["lender"]["nullable"] is True
        assert columns["upfront_fees"]["nullable"] is False
        assert columns["upfront_fees"]["default"] is not None

        with engine.begin() as connection:
            existing = connection.execute(
                text("SELECT lender, upfront_fees, loan_type, currency, housing_costs FROM plans")
            ).one()
            assert existing.lender is None
            assert existing.upfront_fees == Decimal("0.00")
            assert existing.loan_type == "other"
            assert existing.currency == "USD"
            assert existing.housing_costs == {}
            connection.execute(text("UPDATE plans SET upfront_fees = 12"))
            connection.execute(text("UPDATE plans SET upfront_fees = DEFAULT"))
            assert connection.execute(text("SELECT upfront_fees FROM plans")).scalar_one() == Decimal("0.00")

        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(text("UPDATE plans SET upfront_fees = -1"))

        checks = {constraint["name"] for constraint in inspector.get_check_constraints("plans")}
        assert "ck_plans_upfront_fees_non_negative" in checks
    finally:
        engine.dispose()
        command.downgrade(config, "base")
