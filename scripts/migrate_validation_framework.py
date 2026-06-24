"""ATS Validation Framework — Schema Migration
Sprint   : ATS Automation & Data Quality
Branch   : feature/ats-validation-framework

Idempotent: safe to run multiple times.
Columns already present are skipped without error.
Backfill guards (validation_status IS NULL) prevent re-processing on re-runs.

Usage:
    python3 scripts/migrate_validation_framework.py

Expected output — first run:
    [M1] Added column: validation_status
    [M2] Added column: validated_at
    [Backfill-1] N EXPIRED rows updated (validation_status + validated_at)
    [Backfill-2] N NULL-URL NEW rows set to SUSPECT
    Migration complete.

Expected output — subsequent runs (idempotent):
    [M1] Skipped: validation_status already exists
    [M2] Skipped: validated_at already exists
    [Backfill-1] 0 EXPIRED rows updated (already backfilled)
    [Backfill-2] 0 NULL-URL NEW rows set to SUSPECT (already backfilled)
    Migration complete.

Exit codes:
    0 — Migration completed successfully
    2 — Fatal: database unavailable or unrecoverable error
"""

import sqlite3
import sys

DB_PATH = "database/ats.db"


def column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    """Return True if `column` exists in `table`.
    Uses PRAGMA table_info — compatible with all SQLite versions >= 3.0.
    Does not require ALTER TABLE ... ADD COLUMN IF NOT EXISTS (SQLite >= 3.37.0).
    """
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def main() -> None:
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
    except sqlite3.Error as exc:
        print(f"FATAL: Cannot connect to database: {exc}", file=sys.stderr)
        sys.exit(2)

    # ── M1: validation_status ────────────────────────────────────────────────
    # Three-state validation outcome for this job's URL.
    # Values : ACTIVE | SUSPECT | EXPIRED
    # NULL   : never validated under this framework
    if not column_exists(cursor, "jobs", "validation_status"):
        cursor.execute("ALTER TABLE jobs ADD COLUMN validation_status TEXT")
        print("[M1] Added column: validation_status")
    else:
        print("[M1] Skipped: validation_status already exists")

    # ── M2: validated_at ─────────────────────────────────────────────────────
    # ISO 8601 timestamp of the most recent validation attempt.
    # NULL = never validated. Distinct from expired_at (EXPIRED-only timestamp).
    if not column_exists(cursor, "jobs", "validated_at"):
        cursor.execute("ALTER TABLE jobs ADD COLUMN validated_at TEXT")
        print("[M2] Added column: validated_at")
    else:
        print("[M2] Skipped: validated_at already exists")

    # ── Backfill 1: existing EXPIRED rows ────────────────────────────────────
    # Rows with status='EXPIRED' were confirmed dead before this framework
    # existed. validation_status must not be NULL on them — NULL would
    # incorrectly imply "never validated" and corrupt reporting totals.
    # validated_at is set to migration timestamp as a proxy: these rows were
    # not checked by the new framework, but NULL would be misleading.
    # Guard: AND validation_status IS NULL — prevents re-processing on re-runs
    # and prevents overwriting validated_at on rows the new validator has
    # already processed.
    cursor.execute("""
        UPDATE jobs
           SET validation_status = 'EXPIRED',
               validated_at      = strftime('%Y-%m-%dT%H:%M:%S', 'now')
         WHERE status            = 'EXPIRED'
           AND validation_status IS NULL
    """)
    print(
        f"[Backfill-1] {cursor.rowcount} EXPIRED rows updated "
        f"(validation_status + validated_at)"
    )

    # ── Backfill 2: NEW jobs with no URL ─────────────────────────────────────
    # A job with no URL cannot be validated. After the Apply Queue filter
    # switches to validation_status='ACTIVE', NULL-URL jobs would silently
    # disappear from the queue with no report entry. SUSPECT surfaces them
    # for manual review instead.
    # Guard: AND validation_status IS NULL — prevents validated_at from being
    # overwritten on re-runs, preserving the original backfill timestamp.
    cursor.execute("""
        UPDATE jobs
           SET validation_status = 'SUSPECT',
               validated_at      = strftime('%Y-%m-%dT%H:%M:%S', 'now')
         WHERE status            = 'NEW'
           AND (job_url IS NULL OR TRIM(job_url) = '')
           AND validation_status IS NULL
    """)
    print(
        f"[Backfill-2] {cursor.rowcount} NULL-URL NEW rows set to SUSPECT"
    )

    conn.commit()
    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    main()
