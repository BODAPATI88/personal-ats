"""Generate a skills-gap report comparing the resume against currently
tracked (NEW) jobs: which in-demand skills are missing from the resume,
and which resume skills are already strong matches for the job market.

Usage:
    python3 scripts/skills_gap_report.py
"""

import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from skill_utils import load_resume_skills, parse_job_skills

DB_PATH = "database/ats.db"
REPORT_PATH = Path("reports/skills_gap_report.txt")
TOP_N = 15


def main():
    resume_skills = load_resume_skills()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT title, skills FROM jobs WHERE UPPER(status)='NEW'")
        rows = cursor.fetchall()
    except sqlite3.OperationalError as e:
        conn.close()
        if "no such column: skills" in str(e):
            print(
                "Error: jobs table is missing the 'skills' column.\n"
                "Run `python3 scripts/migrate_db.py` once, then re-run this report."
            )
            sys.exit(1)
        raise
    conn.close()

    missing_counter = Counter()
    matched_counter = Counter()
    jobs_considered = 0

    for title, skills_field in rows:
        job_skills = parse_job_skills(skills_field, title)
        if not job_skills:
            continue
        jobs_considered += 1
        for skill in job_skills:
            if skill in resume_skills:
                matched_counter[skill] += 1
            else:
                missing_counter[skill] += 1

    Path("reports").mkdir(exist_ok=True)

    lines = []
    lines.append("Skills Gap Report")
    lines.append("=" * 40)
    lines.append(f"NEW jobs analyzed (with skill data): {jobs_considered}")
    lines.append("")
    lines.append("Top Missing Skills (in demand, not on resume):")

    if jobs_considered and missing_counter:
        for skill, count in missing_counter.most_common(TOP_N):
            pct = round((count / jobs_considered) * 100, 1)
            lines.append(f"  {skill:<25} required in {count} jobs ({pct}%)")
    else:
        lines.append("  None - resume covers all tracked job requirements.")

    lines.append("")
    lines.append("Strongest Matching Skills (on resume, in demand):")

    if jobs_considered and matched_counter:
        for skill, count in matched_counter.most_common(TOP_N):
            pct = round((count / jobs_considered) * 100, 1)
            lines.append(f"  {skill:<25} matched in {count} jobs ({pct}%)")
    else:
        lines.append("  No overlapping skills found.")

    REPORT_PATH.write_text("\n".join(lines) + "\n")
    print(f"Skills gap report written to {REPORT_PATH} ({jobs_considered} jobs analyzed)")


if __name__ == "__main__":
    main()
