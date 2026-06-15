import sqlite3

conn = sqlite3.connect("database/ats.db")
cursor = conn.cursor()

cursor.execute("""
SELECT id,title,company,location,status
FROM jobs
ORDER BY id DESC
""")

rows = cursor.fetchall()

print("\nJob List\n")
print("-" * 80)

for row in rows:
    print(
        f"ID:{row[0]} | "
        f"{row[1]} | "
        f"{row[2]} | "
        f"{row[3]} | "
        f"{row[4]}"
    )

print("-" * 80)

conn.close()
