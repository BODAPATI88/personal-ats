import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from skill_utils import load_resume_skills, parse_job_skills, weighted_match

DB_PATH = "database/ats.db"


def main():
    resume_skills = load_resume_skills()
    if not resume_skills:
        print("Warning: no resume skills loaded from resume/ravi_resume.txt - all scores will be 0.")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, title, skills FROM jobs")
        rows = cursor.fetchall()
    except sqlite3.OperationalError as e:
        if "no such column: skills" in str(e):
            conn.close()
            print(
                "Error: jobs table is missing the 'skills' column.\n"
                "Run `python3 scripts/migrate_db.py` once, then re-run scoring."
            )
            sys.exit(1)
        raise

    updated = 0
    for job_id, title, skills_field in rows:
        job_skills = parse_job_skills(skills_field, title)
        score, _matched, _missing = weighted_match(job_skills, resume_skills)

        cursor.execute(
            "UPDATE jobs SET score=? WHERE id=?",
            (score, job_id)
        )
        updated += 1

    conn.commit()
    conn.close()

    print(f"Job scoring completed. {updated} jobs scored (resume-aware).")


if __name__ == "__main__":
    main()
