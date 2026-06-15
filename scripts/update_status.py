import sqlite3

job_id = input("Job ID: ")
new_status = input("Status: ")

conn = sqlite3.connect("database/ats.db")
cursor = conn.cursor()

cursor.execute(
    "UPDATE jobs SET status = ? WHERE id = ?",
    (new_status, job_id)
)

conn.commit()
conn.close()

print("Status updated.")
