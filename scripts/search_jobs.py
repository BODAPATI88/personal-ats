import sqlite3

keyword = input("Keyword: ")

conn = sqlite3.connect("database/ats.db")
cursor = conn.cursor()

cursor.execute(
    """
    SELECT id,title,company,status
    FROM jobs
    WHERE LOWER(title) LIKE ?
    """,
    (f"%{keyword.lower()}%",)
)

rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()
