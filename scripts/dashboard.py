import sqlite3

conn = sqlite3.connect("database/ats.db")
cursor = conn.cursor()

statuses = [
    "NEW",
    "APPLIED",
    "HR_ROUND",
    "TECHNICAL",
    "FINAL",
    "OFFER",
    "REJECTED"
]

print("\nATS Dashboard\n")
print("-" * 30)

for status in statuses:
    cursor.execute(
        "SELECT COUNT(*) FROM jobs WHERE UPPER(status)=?",
        (status,)
    )
    count = cursor.fetchone()[0]
    print(f"{status:<12}: {count}")

print("-" * 30)

cursor.execute("SELECT COUNT(*) FROM jobs")
total = cursor.fetchone()[0]

print(f"TOTAL JOBS  : {total}")

conn.close()
