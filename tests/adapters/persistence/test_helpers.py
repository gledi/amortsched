import sqlalchemy

from amortsched.adapters.persistence.helpers import build_postgres_upsert_statement

metadata = sqlalchemy.MetaData()

dummy_table = sqlalchemy.Table(
    "dummy",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("tenant_id", sqlalchemy.String),
    sqlalchemy.Column("name", sqlalchemy.String),
    sqlalchemy.Column("value", sqlalchemy.Integer),
)


def test_single_conflict_column():
    values = {"id": "1", "tenant_id": "t1", "name": "n", "value": 42}
    stmt = build_postgres_upsert_statement(dummy_table, values, ("id",))
    compiled = stmt.compile(
        dialect=sqlalchemy.dialects.postgresql.dialect(),
        compile_kwargs={"literal_binds": True},
    )
    sql = str(compiled)
    assert "ON CONFLICT (id)" in sql
    assert "SET tenant_id" in sql
    assert "SET name" in sql or "name =" in sql


def test_multiple_conflict_columns():
    values = {"id": "1", "tenant_id": "t1", "name": "n", "value": 42}
    stmt = build_postgres_upsert_statement(dummy_table, values, ("id", "tenant_id"))
    compiled = stmt.compile(
        dialect=sqlalchemy.dialects.postgresql.dialect(),
        compile_kwargs={"literal_binds": True},
    )
    sql = str(compiled)
    assert "ON CONFLICT (id, tenant_id)" in sql
    assert "tenant_id" not in sql.split("SET", 1)[-1] or "dummy.tenant_id" not in sql.split("SET", 1)[-1]


def test_conflict_columns_excluded_from_update_set():
    values = {"id": "1", "tenant_id": "t1", "name": "n", "value": 42}
    stmt = build_postgres_upsert_statement(dummy_table, values, ("id", "tenant_id"))
    compiled = stmt.compile(
        dialect=sqlalchemy.dialects.postgresql.dialect(),
        compile_kwargs={"literal_binds": True},
    )
    sql = str(compiled)
    set_clause = sql.split("SET", 1)[-1]
    assert "name" in set_clause
    assert "value" in set_clause
