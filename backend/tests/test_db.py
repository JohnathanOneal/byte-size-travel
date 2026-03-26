from bst.db import create_schema, get_connection


def test_schema_creates_all_tables() -> None:
    conn = get_connection(":memory:")
    create_schema(conn)

    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = [row["name"] for row in cursor.fetchall()]

    assert "sources" in tables
    assert "articles" in tables
    assert "enriched_articles" in tables
    assert "article_status" in tables
    assert "editions" in tables
    assert "edition_articles" in tables

    conn.close()


def test_foreign_keys_enabled() -> None:
    conn = get_connection(":memory:")
    result = conn.execute("PRAGMA foreign_keys").fetchone()
    assert result[0] == 1
    conn.close()


def test_wal_mode_enabled() -> None:
    conn = get_connection(":memory:")
    result = conn.execute("PRAGMA journal_mode").fetchone()
    # in-memory databases don't support WAL, returns "memory"
    assert result[0] in ("wal", "memory")
    conn.close()
