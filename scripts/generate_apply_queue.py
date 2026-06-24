import sqlite3
from pathlib import Path

conn = sqlite3.connect("database/ats.db")
cursor = conn.cursor()

cursor.execute("""
SELECT id,title,company,score
FROM jobs
WHERE status='NEW'
AND validation_status='ACTIVE'
ORDER BY score DESC,id DESC
LIMIT 25
""")

rows = cursor.fetchall()

Path("reports").mkdir(exist_ok=True)

with open("reports/today_apply_queue.txt", "w") as f:
    for row in rows:
        f.write(f"{row[0]}|{row[1]}|{row[2]}|{row[3]}\n")

print(f"Generated queue with {len(rows)} jobs")
