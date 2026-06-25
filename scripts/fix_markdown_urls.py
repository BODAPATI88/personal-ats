"""Historical URL Cleanup Script - v1.0.0

Scans the jobs table for malformed (non-HTTP/HTTPS) URLs, repairs them
through the URL sanitizer, and resets validation metadata so Validation
Framework v2.0 reprocesses the corrected rows cleanly on the next run.

Idempotent: rows with URLs already starting with http:// or https:// are
excluded by query scope and are never modified. Running this script twice
produces identical results.

Usage:
    python3 scripts/fix_markdown_urls.py           # live run
    python3 scripts/fix_markdown_urls.py --dry-run # preview, no writes

Exit codes:
    0 — Completed (dry-run or live). All malformed URLs corrected, or none found.
    1 — Completed with one or more URLs that could not be extracted.
    2 — Fatal: database unavailable or unrecoverable startup error.
"""

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Add project root to sys.path so utils/ is importable regardless of the
# working directory from which this script is invoked.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from utils.url_sanitizer import sanitize
except ImportError as exc:
    print(f"FATAL: Cannot import url_sanitizer: {exc}", file=sys.stderr)
    print(
        "Ensure utils/url_sanitizer.py is deployed before running this script.",
        file=sys.stderr,
    )
    sys.exit(2)

DB_PATH     = "database/ats.db"
REPORT_PATH = Path("reports/url_cleanup_report.txt")


def _truncate(value: str, max_len: int = 80) -> str:
    """Truncate a string for report display."""
    return value if len(value) <= max_len else value[: max_len - 3] + "..."


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Repair malformed job URLs in the ATS database."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing to the database.",
    )
    args      = parser.parse_args()
    dry_run   = args.dry_run
    run_start = datetime.now()

    # ── Database ──────────────────────────────────────────────────────────────
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
    except sqlite3.Error as exc:
        print(f"FATAL: Cannot connect to database: {exc}", file=sys.stderr)
        sys.exit(2)

    # ── Fetch counts and malformed rows ───────────────────────────────────────
    try:
        cursor.execute("""
            SELECT COUNT(*)
              FROM jobs
             WHERE job_url IS NOT NULL
               AND TRIM(job_url) != ''
        """)
        total_with_url = cursor.fetchone()[0]

        # Malformed = job_url exists but does not start with http:// or https://
        # LOWER() ensures the check is case-insensitive.
        cursor.execute("""
            SELECT id, job_url, status
              FROM jobs
             WHERE job_url IS NOT NULL
               AND TRIM(job_url) != ''
               AND LOWER(job_url) NOT LIKE 'http://%'
               AND LOWER(job_url) NOT LIKE 'https://%'
        """)
        malformed_rows = cursor.fetchall()
    except sqlite3.Error as exc:
        conn.close()
        print(f"FATAL: Query failed: {exc}", file=sys.stderr)
        sys.exit(2)

    # ── Process each malformed row ────────────────────────────────────────────
    corrected = []   # list of (job_id, original_url, sanitized_url)
    failures  = []   # list of (job_id, original_url, reason)
    ts        = run_start.isoformat(timespec="seconds")

    for job_id, original_url, status in malformed_rows:
        sanitized_url = sanitize(original_url)

        if sanitized_url is None:
            failures.append((
                job_id,
                original_url,
                "sanitizer returned None — no extractable HTTP/HTTPS URL",
            ))
            continue

        if not dry_run:
            try:
                if status == "NEW":
                    # Reset all validation metadata for NEW jobs so
                    # Validation Framework v2.0 reprocesses the row cleanly.
                    # expired_at is cleared because it should not be set on a
                    # NEW job — any prior value resulted from a malformed URL.
                    cursor.execute(
                        """UPDATE jobs
                              SET job_url           = ?,
                                  validation_status = NULL,
                                  validated_at      = NULL,
                                  expired_at        = NULL
                            WHERE id = ?""",
                        (sanitized_url, job_id),
                    )
                else:
                    # Non-NEW jobs: repair URL and reset validation metadata.
                    # Do not clear expired_at — the lifecycle state is settled
                    # for APPLIED, EXPIRED, and other non-NEW rows.
                    cursor.execute(
                        """UPDATE jobs
                              SET job_url           = ?,
                                  validation_status = NULL,
                                  validated_at      = NULL
                            WHERE id = ?""",
                        (sanitized_url, job_id),
                    )
            except sqlite3.Error as exc:
                failures.append((
                    job_id,
                    original_url,
                    f"database write failed: {exc}",
                ))
                continue

        corrected.append((job_id, original_url, sanitized_url))

    if not dry_run:
        conn.commit()
    conn.close()

    # ── Summary stats ─────────────────────────────────────────────────────────
    already_clean = total_with_url - len(malformed_rows)
    mode_label    = "DRY RUN" if dry_run else "LIVE"
    exit_code     = 1 if failures else 0

    # ── Report ────────────────────────────────────────────────────────────────
    try:
        Path("reports").mkdir(exist_ok=True)
        with open(REPORT_PATH, "w") as fh:
            fh.write("URL Cleanup Report\n")
            fh.write("=" * 50 + "\n")
            fh.write(
                f"Generated At    : {run_start.strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            fh.write(f"Mode            : {mode_label}\n")
            fh.write(f"Jobs Scanned    : {total_with_url}\n")
            fh.write(f"Malformed Found : {len(malformed_rows)}\n")
            fh.write(f"Already Clean   : {already_clean}\n")
            if dry_run:
                fh.write(f"Would Correct   : {len(corrected)}\n")
                fh.write(f"Would Fail      : {len(failures)}\n")
            else:
                fh.write(f"Corrected       : {len(corrected)}\n")
                fh.write(f"Failed          : {len(failures)}\n")
            fh.write("=" * 50 + "\n")

            if corrected:
                section = "Would Correct" if dry_run else "Corrected"
                fh.write(f"\n{section}\n")
                for jid, orig, san in corrected:
                    fh.write(f"  Job #{jid}: {_truncate(orig)}\n")
                    fh.write(f"           → {san}\n")

            if failures:
                section = "Would Fail" if dry_run else "Failed (not corrected)"
                fh.write(f"\n{section}\n")
                for jid, orig, reason in failures:
                    fh.write(f"  Job #{jid}: {_truncate(orig)}\n")
                    fh.write(f"           Reason: {reason}\n")

    except OSError as exc:
        # Report write failure is non-fatal — stdout summary still prints
        # and exit code reflects the validation outcome, not I/O state.
        print(f"WARNING: Report write failed: {exc}", file=sys.stderr)

    # ── Stdout summary ────────────────────────────────────────────────────────
    if dry_run:
        print(f"Scanned: {total_with_url}")
        print(f"Malformed Found: {len(malformed_rows)}")
        print(f"Would Correct: {len(corrected)}")
        print(f"Would Fail: {len(failures)}")
    else:
        print(
            f"[LIVE] Scanned {total_with_url} — "
            f"Malformed: {len(malformed_rows)}, "
            f"Corrected: {len(corrected)}, "
            f"Already Clean: {already_clean}, "
            f"Failed: {len(failures)}"
        )
        print(f"Report: {REPORT_PATH}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
