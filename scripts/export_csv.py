import sqlite3
import pandas as pd

conn = sqlite3.connect("database/ats.db")

df = pd.read_sql_query(
    "SELECT * FROM jobs",
    conn
)

df.to_csv(
    "exports/jobs_export.csv",
    index=False
)

conn.close()

print("Export completed")
