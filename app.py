from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

@app.route("/")
def home():

    conn = sqlite3.connect("database/ats.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id,title,company,location,status
    FROM jobs
    ORDER BY id DESC
    """)
    jobs = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM jobs")
    total_jobs = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM jobs WHERE UPPER(status)='APPLIED'"
    )
    applied_jobs = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM jobs WHERE UPPER(status)='NEW'"
    )
    new_jobs = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM jobs WHERE UPPER(status)='OFFER'"
    )
    offer_jobs = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "index.html",
        jobs=jobs,
        total_jobs=total_jobs,
        applied_jobs=applied_jobs,
        new_jobs=new_jobs,
        offer_jobs=offer_jobs
    )

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
