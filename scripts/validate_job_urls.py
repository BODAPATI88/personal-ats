"""Job URL Validation Framework - v2.0.0

Three-state validation for every NEW job with a URL:

  ACTIVE  — No negative signal detected. HTTP 200 with no closed phrase and
             no CAPTCHA phrase in the raw response body.

             ARCHITECTURAL LIMITATION: urllib cannot execute JavaScript.
             ACTIVE means no evidence of closure was found in the raw HTTP
             response. It does not confirm the listing is live on
             JavaScript-rendered job boards (Naukri, LinkedIn, Workday,
             Taleo). SPA boards that have closed a listing may return HTTP 200
             with an empty shell — those listings will be classified ACTIVE.
             This is a known limitation documented in the sprint release notes.

  SUSPECT — Validation inconclusive. Bot-block (403/429), timeout, network
             error, or CAPTCHA page detected. Excluded from Apply Queue;
             retained for review. Preferred outcome when certainty is low —
             false negatives are safer than false expiration.

  EXPIRED — Definitively dead. HTTP 404/410, or a closed phrase matched in
             the raw response body.

Apply Queue eligibility:
    WHERE status = 'NEW' AND validation_status = 'ACTIVE'

Report arithmetic:
    queried  = checked + failures
    checked  = active + suspect + expired + skipped

    skipped  = jobs where network check completed but DB write was skipped
               because status changed between SELECT and UPDATE (correct
               behaviour — not a failure). These retain prior validation_status.

Exit codes:
    0 — Validation completed, zero job-level failures
    1 — Validation completed, one or more job-level failures
    2 — Fatal: database unavailable or unrecoverable startup error

Usage:
    python3 scripts/validate_job_urls.py
"""

import json
import socket
import sqlite3
import sys
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

DB_PATH         = "database/ats.db"
REPORT_PATH     = Path("reports/validation_report.txt")
LOG_PATH        = Path("ats.log")
TIMEOUT_SECONDS = 5
MAX_CONCURRENT  = 10

# Definitive "listing is gone" signals.
# Matched case-insensitively against first BODY_READ_BYTES of response body.
CLOSED_PHRASES = [
    "job no longer available",
    "position filled",
    "posting removed",
    "vacancy closed",
    "no longer accepting applications",
]

# Anti-bot / CAPTCHA signals.
# Checked before CLOSED_PHRASES. A bot-wall page may contain neither an apply
# CTA nor a closure message — it must not be classified ACTIVE. Precedence of
# SUSPECT over EXPIRED when both signals present is intentional per CTO
# Decision 3 (prefer false negative over false expiration).
CAPTCHA_PHRASES = [
    "verify you are human",
    "complete the captcha",
    "are you a robot",
    "security check",
    "unusual traffic from your",
    "access to this page has been denied",
]

BODY_READ_BYTES = 20_000
USER_AGENT      = "Mozilla/5.0 (compatible; PersonalATS-URLValidator/2.0)"

STATUS_ACTIVE  = "ACTIVE"
STATUS_SUSPECT = "SUSPECT"
STATUS_EXPIRED = "EXPIRED"


def check_url(job_id: int, url: str) -> tuple:
    """Check a single job URL. Returns (job_id, validation_status, reason).

    Raises ValueError for non-HTTP/HTTPS schemes or malformed URL construction.
    Caller treats these as Failures (data quality defect), not SUSPECT
    (network outcome). All genuine network exceptions are caught internally
    and returned as SUSPECT.
    """
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError(f"non-HTTP/HTTPS scheme: {url[:80]}")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    except ValueError as exc:
        raise ValueError(f"malformed URL: {exc}") from exc

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            status_code = resp.getcode()
            body = resp.read(BODY_READ_BYTES).decode("utf-8", errors="ignore").lower()

    except urllib.error.HTTPError as exc:
        if exc.code in (404, 410):
            return (job_id, STATUS_EXPIRED, f"HTTP {exc.code}")
        if exc.code in (403, 429):
            return (job_id, STATUS_SUSPECT, f"HTTP {exc.code} (bot-blocked)")
        return (job_id, STATUS_SUSPECT, f"HTTP {exc.code} (inconclusive)")

    except urllib.error.URLError as exc:
        # urllib wraps socket.timeout in URLError.reason on Python <= 3.10.
        # On Python 3.11+, socket.timeout is an alias for TimeoutError.
        # Handled here with isinstance check to avoid a separate
        # `except TimeoutError` block that is dead code on Python < 3.11.
        if isinstance(exc.reason, (socket.timeout, TimeoutError)):
            return (job_id, STATUS_SUSPECT, f"timeout ({TIMEOUT_SECONDS}s exceeded)")
        return (job_id, STATUS_SUSPECT, f"network error: {exc.reason}")

    except OSError as exc:
        # Catches direct TimeoutError / socket.timeout raises on Python 3.11+
        # and other OS-level connection failures not wrapped by urllib.
        if isinstance(exc, (TimeoutError, socket.timeout)):
            return (job_id, STATUS_SUSPECT, f"timeout ({TIMEOUT_SECONDS}s exceeded)")
        return (job_id, STATUS_SUSPECT, f"OS error: {exc}")

    # CAPTCHA check before closed-phrase check — a bot-wall page must not be
    # classified ACTIVE even if it contains no closure message.
    for phrase in CAPTCHA_PHRASES:
        if phrase in body:
            return (job_id, STATUS_SUSPECT, f"anti-bot/CAPTCHA: '{phrase}'")

    for phrase in CLOSED_PHRASES:
        if phrase in body:
            return (job_id, STATUS_EXPIRED, f"closed phrase: '{phrase}'")

    return (job_id, STATUS_ACTIVE, f"HTTP {status_code} — no negative signal detected")


def write_log(record: dict) -> None:
    """Append one JSON line to ats.log.
    Never raises — a log infrastructure failure must not abort a validation run.
    """
    try:
        with open(LOG_PATH, "a") as fh:
            fh.write(json.dumps(record) + "\n")
    except OSError:
        pass


def _write_report(
    summary: dict,
    results: dict,
    failures: list,
    skipped: int,
) -> None:
    """Write the human-readable validation report.

    Raises OSError on I/O failure — caller catches, logs, and continues
    so that a report write failure does not suppress the run log entry
    or change the exit code.
    """
    Path("reports").mkdir(exist_ok=True)
    with open(REPORT_PATH, "w") as fh:
        fh.write("Validation Report\n")
        fh.write("=" * 50 + "\n")
        fh.write(f"Generated At  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        fh.write(f"Jobs Queried  : {summary['queried']}\n")
        fh.write(f"Checked       : {summary['checked']}\n")
        fh.write(f"ACTIVE        : {summary['active']}\n")
        fh.write(f"SUSPECT       : {summary['suspect']}\n")
        fh.write(f"EXPIRED       : {summary['expired']}\n")
        fh.write(f"Skipped       : {summary['skipped']}\n")
        fh.write(f"Failures      : {summary['failures']}\n")
        fh.write("=" * 50 + "\n")

        if results[STATUS_SUSPECT]:
            fh.write("\nSUSPECT Jobs\n")
            for jid, reason in results[STATUS_SUSPECT]:
                fh.write(f"  Job #{jid}: {reason}\n")

        if results[STATUS_EXPIRED]:
            fh.write("\nEXPIRED Jobs\n")
            for jid, reason in results[STATUS_EXPIRED]:
                fh.write(f"  Job #{jid}: {reason}\n")

        if failures:
            fh.write("\nFailures (validation not attempted)\n")
            for jid, reason in failures:
                fh.write(f"  Job #{jid}: {reason}\n")

        if skipped:
            fh.write(
                f"\nSkipped (status changed between SELECT and UPDATE): "
                f"{skipped} job(s)\n"
            )


def main() -> None:
    run_start = datetime.now()

    # ── Database connection ───────────────────────────────────────────────────
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
    except sqlite3.Error as exc:
        write_log({
            "timestamp" : run_start.isoformat(timespec="seconds"),
            "event"     : "validation_fatal",
            "error"     : str(exc),
            "exit_code" : 2,
        })
        print(f"FATAL: Cannot connect to database: {exc}", file=sys.stderr)
        sys.exit(2)

    # ── Fetch candidates ──────────────────────────────────────────────────────
    try:
        cursor.execute("""
            SELECT id, job_url FROM jobs
            WHERE  status  = 'NEW'
              AND  job_url IS NOT NULL
              AND  TRIM(job_url) != ''
        """)
        rows = cursor.fetchall()
    except sqlite3.Error as exc:
        conn.close()
        write_log({
            "timestamp" : run_start.isoformat(timespec="seconds"),
            "event"     : "validation_fatal",
            "error"     : str(exc),
            "exit_code" : 2,
        })
        print(f"FATAL: Query failed: {exc}", file=sys.stderr)
        sys.exit(2)

    # ── Validation ────────────────────────────────────────────────────────────
    results  = {STATUS_ACTIVE: [], STATUS_SUSPECT: [], STATUS_EXPIRED: []}
    failures = []   # (job_id, reason) — data/infra errors; no write attempted
    checked  = 0    # network validation completed without exception
    skipped  = 0    # validated but write skipped (status changed mid-run)
    ts       = run_start.isoformat(timespec="seconds")

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as pool:
        futures = {
            pool.submit(check_url, job_id, url): job_id
            for job_id, url in rows
        }
        for future in as_completed(futures):
            job_id = futures[future]
            try:
                job_id, validation_status, reason = future.result()
            except Exception as exc:
                # ValueError (malformed URL / non-HTTP scheme) or unexpected
                # raise in check_url. Recorded as Failure — validation_status
                # is not written so the job retains its current state and is
                # retried on the next run.
                failures.append((job_id, str(exc)))
                continue

            checked += 1

            if validation_status == STATUS_EXPIRED:
                # Write validation fields AND update lifecycle status for
                # backward compatibility with consumers still reading
                # status='EXPIRED'. expired_at behaviour unchanged from v1.5.1.
                cursor.execute(
                    """UPDATE jobs
                          SET status            = 'EXPIRED',
                              expired_at        = ?,
                              validation_status = 'EXPIRED',
                              validated_at      = ?
                        WHERE id     = ?
                          AND status = 'NEW'""",
                    (ts, ts, job_id),
                )
            else:
                cursor.execute(
                    """UPDATE jobs
                          SET validation_status = ?,
                              validated_at      = ?
                        WHERE id     = ?
                          AND status = 'NEW'""",
                    (validation_status, ts, job_id),
                )

            if cursor.rowcount:
                results[validation_status].append((job_id, reason))
            else:
                # rowcount == 0: job status changed between SELECT and UPDATE.
                # The network check was completed and is counted in `checked`,
                # but the write was correctly skipped by WHERE status='NEW'.
                skipped += 1

    conn.commit()
    conn.close()

    # ── Exit code resolved before I/O ─────────────────────────────────────────
    exit_code = 1 if failures else 0

    summary = {
        "timestamp" : run_start.isoformat(timespec="seconds"),
        "event"     : "validation_run_complete",
        "queried"   : len(rows),
        "checked"   : checked,
        "active"    : len(results[STATUS_ACTIVE]),
        "suspect"   : len(results[STATUS_SUSPECT]),
        "expired"   : len(results[STATUS_EXPIRED]),
        "skipped"   : skipped,
        "failures"  : len(failures),
        "exit_code" : exit_code,
    }

    # ── Log fires first ───────────────────────────────────────────────────────
    # Run result is persisted before report write is attempted. A report I/O
    # failure cannot suppress the log entry. write_log swallows OSError
    # internally — a log infrastructure failure must not abort the run.
    write_log(summary)

    # ── Report is best-effort ─────────────────────────────────────────────────
    # Failure is caught, logged separately, and printed to stderr. It does not
    # change exit_code — a report I/O failure is an infrastructure concern,
    # not a validation failure.
    try:
        _write_report(summary, results, failures, skipped)
    except OSError as exc:
        write_log({
            "timestamp" : datetime.now().isoformat(timespec="seconds"),
            "event"     : "report_write_failed",
            "error"     : str(exc),
        })
        print(f"WARNING: Report write failed: {exc}", file=sys.stderr)

    # ── Stdout summary ────────────────────────────────────────────────────────
    print(
        f"Checked {checked}/{len(rows)} NEW jobs — "
        f"ACTIVE: {len(results[STATUS_ACTIVE])}, "
        f"SUSPECT: {len(results[STATUS_SUSPECT])}, "
        f"EXPIRED: {len(results[STATUS_EXPIRED])}, "
        f"Skipped: {skipped}, "
        f"Failures: {len(failures)}"
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
