"""Expired Job URL Validator - v1.5.1

Checks job_url for every job currently in NEW status and flips dead
listings to EXPIRED. Runs as part of the daily pipeline, between
import and scoring, so dead jobs never reach scoring, recommendations,
or the apply queue - both recommend_jobs.py and generate_apply_queue.py
already filter strictly on status='NEW', so an EXPIRED job is excluded
from them automatically with no further changes needed there.

Conservative by design: a job is only marked EXPIRED on a definitive
"this listing is gone" signal - HTTP 404/410, or page text matching a
known closed-posting phrase (job no longer available, position
filled, posting removed, vacancy closed, no longer accepting
applications). Timeouts, connection errors, 403 (bot-blocked), and
429 (rate-limited) are inconclusive, not evidence the job is gone -
those jobs are left untouched for the next run to re-check rather
than risk a false positive.

No 30-day or other age restriction: every NEW job with a URL is
checked on every run.

Safe to run repeatedly; only ever updates rows that are still
status='NEW' at write time.

Usage:
    python3 scripts/validate_job_urls.py
"""

import sqlite3
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

DB_PATH = "database/ats.db"
REPORT_PATH = Path("reports/expired_jobs.txt")

TIMEOUT_SECONDS = 5
MAX_CONCURRENT = 10

# Definitive "listing is gone" signals only. Matched case-insensitively
# against the first chunk of response body text.
CLOSED_PHRASES = [
    "job no longer available",
    "position filled",
    "posting removed",
    "vacancy closed",
    "no longer accepting applications",
]

# HTTP statuses that mean "the check itself was blocked", not "the job
# is gone". Never treated as evidence of expiry.
INCONCLUSIVE_STATUSES = {403, 429}

# How much of the response body to read when checking for closed-phrase
# text. Job-closed banners appear early in the page; capping this keeps
# large pages from slowing down the concurrent check pool.
BODY_READ_BYTES = 20000

USER_AGENT = "Mozilla/5.0 (compatible; PersonalATS-URLValidator/1.0)"


def check_url(job_id, url):
    """Check a single job URL. Returns (job_id, is_expired, reason).

    is_expired is True only on a definitive dead-listing signal -
    never on timeouts, network errors, or bot-blocking responses.
    """
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            status_code = resp.getcode()
            body = resp.read(BODY_READ_BYTES).decode("utf-8", errors="ignore").lower()
    except urllib.error.HTTPError as e:
        if e.code in (404, 410):
            return (job_id, True, f"HTTP {e.code}")
        if e.code in INCONCLUSIVE_STATUSES:
            return (job_id, False, f"HTTP {e.code} (inconclusive, not marked expired)")
        return (job_id, False, f"HTTP {e.code} (inconclusive, not marked expired)")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return (job_id, False, f"network error: {e} (inconclusive, not marked expired)")

    for phrase in CLOSED_PHRASES:
        if phrase in body:
            return (job_id, True, f"page text matched '{phrase}'")

    return (job_id, False, f"HTTP {status_code} - live")


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, job_url FROM jobs
        WHERE status='NEW' AND job_url IS NOT NULL AND TRIM(job_url) != ''
    """)
    rows = cursor.fetchall()

    expired = []
    checked = 0

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as pool:
        futures = {pool.submit(check_url, job_id, url): job_id for job_id, url in rows}
        for future in as_completed(futures):
            job_id, is_expired, reason = future.result()
            checked += 1
            if is_expired:
                # Re-check status='NEW' at write time in case it changed
                # between the initial SELECT and now.
                cursor.execute(
                    "UPDATE jobs SET status='EXPIRED', expired_at=? "
                    "WHERE id=? AND status='NEW'",
                    (datetime.now().isoformat(timespec="seconds"), job_id),
                )
                if cursor.rowcount:
                    expired.append((job_id, reason))

    conn.commit()
    conn.close()

    Path("reports").mkdir(exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        f.write("Expired Jobs Report\n")
        f.write("=" * 50 + "\n")
        f.write(f"Generated At : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Jobs Checked : {checked}\n")
        f.write(f"Jobs Expired : {len(expired)}\n\n")
        for job_id, reason in expired:
            f.write(f"  Job #{job_id}: {reason}\n")

    print(f"Checked {checked} NEW jobs with a URL, marked {len(expired)} as EXPIRED")


if __name__ == "__main__":
    main()
