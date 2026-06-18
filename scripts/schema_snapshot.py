"""Schema Snapshot - v1.4

Documents the *actual* current database schema by introspecting the
live SQLite file directly (tables, columns, indexes, row counts).

This exists because no CREATE TABLE statement exists anywhere in this
codebase - the `jobs` table schema only exists implicitly through how
scripts query it. Before Phase 3 adds `application_history` and
`resume_versions`, this snapshot is the source of truth for what the
production database actually looks like, so those migrations aren't
written against guesswork.

Read-only: never writes to the database, safe to run repeatedly.

Usage:
    python3 scripts/schema_snapshot.py [path/to/database.db]

Defaults to database/ats.db when no path is given. Always run this
against the live VM database (not a local/test copy) before writing
Phase 3 migrations, since that's the schema they'll actually run
against.
"""

import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_DB_PATH = "database/ats.db"
REPORT_PATH = Path("reports/schema_snapshot.txt")


def get_tables(cursor):
    cursor.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    )
    return [row[0] for row in cursor.fetchall()]


def get_columns(cursor, table):
    """Returns rows of (cid, name, type, notnull, default, is_pk)."""
    cursor.execute(f"PRAGMA table_info('{table}')")
    return cursor.fetchall()


def get_indexes(cursor, table):
    cursor.execute(f"PRAGMA index_list('{table}')")
    indexes = []
    for idx in cursor.fetchall():
        # idx layout: seq, name, unique, origin, partial
        index_name = idx[1]
        is_unique = bool(idx[2])
        cursor.execute(f"PRAGMA index_info('{index_name}')")
        columns = [col_row[2] for col_row in cursor.fetchall()]
        indexes.append({"name": index_name, "unique": is_unique, "columns": columns})
    return indexes


def get_row_count(cursor, table):
    try:
        cursor.execute(f"SELECT COUNT(*) FROM '{table}'")
        return cursor.fetchone()[0]
    except sqlite3.OperationalError:
        return None


def build_snapshot(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tables = get_tables(cursor)

    lines = []
    lines.append("Database Schema Snapshot")
    lines.append("=" * 50)
    lines.append(f"Database Path : {os.path.abspath(db_path)}")
    lines.append(f"Generated At  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Tables Found  : {len(tables)}")
    lines.append("")

    for table in tables:
        row_count = get_row_count(cursor, table)
        lines.append(f"Table: {table}")
        lines.append("-" * 50)
        lines.append(f"Row Count: {row_count if row_count is not None else 'unknown'}")
        lines.append("")
        lines.append("Columns:")
        for cid, name, col_type, notnull, default, is_pk in get_columns(cursor, table):
            flags = []
            if is_pk:
                flags.append("PRIMARY KEY")
            if notnull:
                flags.append("NOT NULL")
            if default is not None:
                flags.append(f"DEFAULT {default}")
            flag_str = f" ({', '.join(flags)})" if flags else ""
            lines.append(f"  {name:<20} {col_type or 'UNKNOWN':<15}{flag_str}")

        indexes = get_indexes(cursor, table)
        lines.append("")
        if indexes:
            lines.append("Indexes:")
            for idx in indexes:
                prefix = "UNIQUE " if idx["unique"] else ""
                lines.append(f"  {prefix}{idx['name']}: ({', '.join(idx['columns'])})")
        else:
            lines.append("Indexes: none")

        lines.append("")

    conn.close()
    return tables, "\n".join(lines) + "\n"


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB_PATH

    if not os.path.exists(db_path):
        print(f"Error: database not found at {db_path}")
        sys.exit(1)

    tables, snapshot_text = build_snapshot(db_path)

    REPORT_PATH.parent.mkdir(exist_ok=True)
    REPORT_PATH.write_text(snapshot_text)

    print(f"Schema snapshot written to {REPORT_PATH}")
    print(f"Source database: {os.path.abspath(db_path)}")
    print(f"Tables found: {', '.join(tables) if tables else '(none)'}")


if __name__ == "__main__":
    main()
