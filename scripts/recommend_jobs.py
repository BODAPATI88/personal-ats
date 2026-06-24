import sqlite3
from pathlib import Path

DB_PATH = "database/ats.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
SELECT id, company, title, score
FROM jobs
WHERE status='NEW'
AND validation_status='ACTIVE'
ORDER BY company, score DESC, id DESC
""")

rows = cursor.fetchall()
conn.close()

Path("reports").mkdir(exist_ok=True)

# Rows are ordered by company then score DESC, so the first row seen for
# each company is already that company's best-scoring NEW job.
best_per_company = {}
for job_id, company, title, score in rows:
    key = (company or "").strip().lower()
    if key not in best_per_company:
        best_per_company[key] = (job_id, company, title, score)

recommendations = sorted(best_per_company.values(), key=lambda r: r[3], reverse=True)

with open("reports/today_recommendations.txt", "w") as f:
    for job_id, company, title, score in recommendations:

        if score >= 35:
            recommendation = "APPLY"
        elif score >= 20:
            recommendation = "REVIEW"
        else:
            recommendation = "SKIP"

        f.write(
            f"{job_id}|{company}|{title}|{score}|{recommendation}\n"
        )

print(f"Generated {len(recommendations)} company-level recommendations (from {len(rows)} NEW jobs)")
