"""One-time migration: add the `expired_at` column to the jobs table.

Part of ATS v1.5.1 (expired job detection). Nullable TEXT timestamp,
set only when a job's status is changed to EXPIRED - either
automatically by scripts/validate_job_urls.py, or manually via the
"Mark as Expired" action on the Job Detail page. Cleared back to NULL
if a job's status is later changed away from EXPIRED.

Purely additive: no existing column, table, or data is touched.
Safe to run more than once.

Usage:
    python3 scripts/migrate_add_expired_at.py
"""

import sqlite3

DB_PATH = "database/ats.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE jobs ADD COLUMN expired_at TEXT")
        conn.commit()
        print("Added 'expired_at' column to jobs table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("'expired_at' column already exists. Nothing to do.")
        else:
            raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
