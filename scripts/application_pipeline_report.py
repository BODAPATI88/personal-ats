"""Application Pipeline Report - v1.4

Full status-pipeline breakdown and submission/success metrics, written
to reports/application_pipeline.txt. Reuses the same counting logic as
the dashboard's Overview/Pipeline sections (fetch_overview,
fetch_pipeline in dashboard.py) so the report and the dashboard can
never drift apart on these numbers.

Usage:
    python3 scripts/application_pipeline_report.py
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from dashboard import connect, fetch_overview, fetch_pipeline

REPORT_PATH = Path("reports/application_pipeline.txt")


def render(overview, pipeline):
    lines = []
    lines.append("Application Pipeline Report")
    lines.append("=" * 50)
    lines.append(f"Generated At : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append(f"Total Jobs    : {overview['total_jobs']}")
    lines.append(f"New Jobs      : {overview['new_jobs']}")
    lines.append(f"Applied Jobs  : {overview['applied_jobs']}")
    lines.append(f"Success Rate  : {overview['success_rate']}%")
    lines.append("")
    lines.append("Pipeline Breakdown:")
    for status, count in pipeline.items():
        lines.append(f"  {status:<12}: {count}")

    return "\n".join(lines) + "\n"


def main():
    conn = connect()
    try:
        overview = fetch_overview(conn)
        pipeline = fetch_pipeline(conn)
    finally:
        conn.close()

    REPORT_PATH.parent.mkdir(exist_ok=True)
    REPORT_PATH.write_text(render(overview, pipeline))

    print(f"Application pipeline report written to {REPORT_PATH}")


if __name__ == "__main__":
    main()
