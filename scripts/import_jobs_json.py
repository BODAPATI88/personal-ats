import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from db_utils import execute_query, fetch_one

json_file = Path("imports/jobs/sample_jobs.json")

jobs = json.loads(json_file.read_text())

imported = 0
skipped = 0

for job in jobs:
    job_url = job.get("job_url")

    existing = fetch_one(
        "SELECT id FROM jobs WHERE job_url = ?",
        (job_url,)
    )

    if existing:
        skipped += 1
        continue

    execute_query(
        """
        INSERT INTO jobs
        (title, company, location, source, job_url, score, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job.get("title"),
            job.get("company"),
            job.get("location"),
            job.get("source"),
            job.get("job_url"),
            job.get("score", 0),
            job.get("status", "NEW")
        )
    )

    imported += 1

print(f"Imported: {imported}")
print(f"Skipped: {skipped}")
