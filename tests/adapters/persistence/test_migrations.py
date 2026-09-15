from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_initial_migration_builds_schema(postgres, monkeypatch):
    database_url = postgres.get_connection_url(driver="psycopg")
    monkeypatch.setenv("DATABASE__DSN", database_url)
    config = Config("alembic.ini")

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        assert {"alembic_version", "users", "profiles", "plans", "schedules", "refresh_tokens"} <= set(
            inspector.get_table_names()
        )
    finally:
        engine.dispose()
        command.downgrade(config, "base")
