import sqlite3
import pandas as pd

df = pd.read_csv("jobs.csv")

conn = sqlite3.connect("database/ats.db")

df.to_sql(
    "jobs",
    conn,
    if_exists="append",
    index=False
)

conn.close()

print(f"Imported {len(df)} jobs")
