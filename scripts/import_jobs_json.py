import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from db_utils import execute_query, fetch_one
from utils.url_sanitizer import sanitize

json_file = Path(
    sys.argv[1]
    if len(sys.argv) > 1
    else "imports/jobs/sample_jobs.json"
)

jobs = json.loads(json_file.read_text())

imported = 0
skipped = 0

for job in jobs:
    job_url = job.get("job_url")
    job_url = sanitize(job_url)
    company = job.get("company")

    existing_company = fetch_one(
        "SELECT id FROM jobs WHERE UPPER(company)=UPPER(?) AND UPPER(status)='APPLIED'",
        (company,)
    )

    if existing_company:
        skipped += 1
        continue


    existing = fetch_one(
    """
    SELECT id
    FROM jobs
    WHERE (
        job_url = ?
        AND job_url IS NOT NULL
    )
    OR (
        UPPER(company)=UPPER(?)
        AND UPPER(title)=UPPER(?)
    )
    """,
    (
        job_url,
        company,
        job.get("title")
    )
)

    if existing:
        skipped += 1
        continue

    skills = job.get("primary_skills") or job.get("skills") or []
    skills_value = ", ".join(skills) if isinstance(skills, list) else str(skills)

    execute_query(
        """
        INSERT INTO jobs
        (title, company, location, source, job_url, score, status, skills)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job.get("title"),
            job.get("company"),
            job.get("location"),
            job.get("source"),
            job_url,
            0,
            job.get("status", "NEW"),
            skills_value
        )
    )

    imported += 1

print(f"Imported: {imported}")
print(f"Skipped: {skipped}")
