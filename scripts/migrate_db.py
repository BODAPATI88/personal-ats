"""One-time migration: add the `skills` column to the jobs table.

Required before using resume-aware scoring or the skills gap report,
since those depend on each job's required skills being stored.
Safe to run more than once.

Usage:
    python3 scripts/migrate_db.py
"""

import sqlite3

DB_PATH = "database/ats.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE jobs ADD COLUMN skills TEXT")
        conn.commit()
        print("Added 'skills' column to jobs table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("'skills' column already exists. Nothing to do.")
        else:
            raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
