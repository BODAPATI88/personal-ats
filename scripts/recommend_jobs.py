import sqlite3
from pathlib import Path

conn = sqlite3.connect("database/ats.db")
cursor = conn.cursor()

cursor.execute("""
SELECT id, company, title, score
FROM jobs
WHERE status='NEW'
ORDER BY score DESC, id DESC
LIMIT 50
""")

rows = cursor.fetchall()

Path("reports").mkdir(exist_ok=True)

with open("reports/today_recommendations.txt", "w") as f:
    for job_id, company, title, score in rows:

        if score >= 35:
            recommendation = "APPLY"
        elif score >= 20:
            recommendation = "REVIEW"
        else:
            recommendation = "SKIP"

        f.write(
            f"{job_id}|{company}|{title}|{score}|{recommendation}\n"
        )

print(f"Generated recommendations for {len(rows)} jobs")
