"""Top Companies Report - v1.4

Full company rankings (not just the dashboard's top-5 snapshot): every
company by job volume, and every company meeting the minimum job
threshold (MIN_JOBS_FOR_TARGET_COMPANY) ranked by average ATS match
score. Reuses dashboard.py's fetch_company_insights so the ranking
logic can't drift between the report and the dashboard.

Usage:
    python3 scripts/top_companies_report.py
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from dashboard import MIN_JOBS_FOR_TARGET_COMPANY, connect, fetch_company_insights

REPORT_PATH = Path("reports/top_companies.txt")

# No artificial cap for the full report - list every company.
REPORT_LIMIT = 10_000


def render(by_volume, top_targets):
    lines = []
    lines.append("Top Companies Report")
    lines.append("=" * 50)
    lines.append(f"Generated At : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("Top Companies by Job Count:")
    if not by_volume:
        lines.append("  No companies tracked yet.")
    for company, count in by_volume:
        lines.append(f"  {company:<30}: {count}")

    lines.append("")
    lines.append(f"Top Target Companies (min {MIN_JOBS_FOR_TARGET_COMPANY} jobs, by avg score):")
    if not top_targets:
        lines.append(f"  No company has {MIN_JOBS_FOR_TARGET_COMPANY}+ tracked jobs yet.")
    for company, avg_score, count in top_targets:
        lines.append(f"  {company:<30}: avg score {avg_score} ({count} jobs)")

    return "\n".join(lines) + "\n"


def main():
    conn = connect()
    try:
        by_volume, top_targets = fetch_company_insights(conn, limit=REPORT_LIMIT)
    finally:
        conn.close()

    REPORT_PATH.parent.mkdir(exist_ok=True)
    REPORT_PATH.write_text(render(by_volume, top_targets))

    print(f"Top companies report written to {REPORT_PATH}")


if __name__ == "__main__":
    main()
