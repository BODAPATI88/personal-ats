"""Company Summary Report - v1.4

Per-company breakdown: job count, average ATS match score, and a full
pipeline status breakdown, across every company with at least one
tracked job.

Unlike the dashboard's "Top Companies" sections (a top-5 snapshot),
this report covers every company, for a full review rather than a
quick glance.

Usage:
    python3 scripts/company_summary.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from dashboard import PIPELINE_STATUSES, connect

REPORT_PATH = Path("reports/company_summary.txt")


def fetch_company_summary(conn):
    cur = conn.cursor()
    cur.execute(
        "SELECT company, COUNT(*) as c, AVG(score) as avg_score FROM jobs "
        "WHERE company IS NOT NULL AND TRIM(company) != '' "
        "GROUP BY company ORDER BY c DESC, avg_score DESC"
    )
    companies = cur.fetchall()

    summary = []
    for company, count, avg_score in companies:
        status_counts = {}
        for status in PIPELINE_STATUSES:
            cur.execute(
                "SELECT COUNT(*) FROM jobs WHERE company=? AND UPPER(status)=?",
                (company, status),
            )
            status_counts[status] = cur.fetchone()[0]
        summary.append((company, count, round(avg_score or 0, 1), status_counts))

    return summary


def render(summary):
    lines = []
    lines.append("Company Summary Report")
    lines.append("=" * 60)
    lines.append(f"Companies tracked: {len(summary)}")
    lines.append("")

    if not summary:
        lines.append("No companies tracked yet.")

    for company, count, avg_score, status_counts in summary:
        lines.append(company)
        lines.append("-" * 60)
        lines.append(f"  Jobs Tracked    : {count}")
        lines.append(f"  Avg Match Score : {avg_score}")
        status_line = " | ".join(f"{s}:{c}" for s, c in status_counts.items())
        lines.append(f"  Pipeline        : {status_line}")
        lines.append("")

    return "\n".join(lines) + "\n"


def main():
    conn = connect()
    try:
        summary = fetch_company_summary(conn)
    finally:
        conn.close()

    REPORT_PATH.parent.mkdir(exist_ok=True)
    REPORT_PATH.write_text(render(summary))

    print(f"Company summary written to {REPORT_PATH} ({len(summary)} companies)")


if __name__ == "__main__":
    main()
