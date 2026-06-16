import sqlite3

KEYWORDS = {
    "kubernetes": 25,
    "azure": 20,
    "terraform": 15,
    "devops": 15,
    "platform": 10,
    "site reliability": 10,
    "sre": 10,
    "cloud": 5,
    "linux": 5,
}

conn = sqlite3.connect("database/ats.db")
cursor = conn.cursor()

cursor.execute("""
SELECT id, title
FROM jobs
""")

for job_id, title in cursor.fetchall():
    title_lower = title.lower()
    score = 0

    for keyword, weight in KEYWORDS.items():
        if keyword in title_lower:
            score += weight

    score = min(score, 100)

    cursor.execute(
        "UPDATE jobs SET score=? WHERE id=?",
        (score, job_id)
    )

conn.commit()
conn.close()

print("Job scoring completed.")
