import sqlite3

title = input("Job Title: ")
company = input("Company: ")
location = input("Location: ")
source = input("Source: ")

conn = sqlite3.connect("database/ats.db")
cursor = conn.cursor()

cursor.execute("""
INSERT INTO jobs
(title, company, location, source)
VALUES (?, ?, ?, ?)
""", (title, company, location, source))

conn.commit()
conn.close()

print("Job added successfully.")
