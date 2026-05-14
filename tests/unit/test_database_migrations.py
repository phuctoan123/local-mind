import sqlite3

from app.database import MIGRATIONS, migration_status, run_migrations


def test_run_migrations_creates_schema_and_records_versions():
    conn = _memory_conn()

    applied = run_migrations(conn)
    status = migration_status(conn)

    assert [migration.version for migration in applied] == [1, 2]
    assert status["latest"] == max(migration.version for migration in MIGRATIONS)
    assert status["applied"] == [1, 2]
    assert status["pending"] == []
    assert _table_exists(conn, "documents")
    assert _table_exists(conn, "collections")
    assert _table_exists(conn, "collection_documents")


def test_run_migrations_is_idempotent():
    conn = _memory_conn()

    first = run_migrations(conn)
    second = run_migrations(conn)

    assert len(first) == len(MIGRATIONS)
    assert second == []
    assert conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0] == len(MIGRATIONS)


def _memory_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _table_exists(conn, table_name: str) -> bool:
    return bool(
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
    )
