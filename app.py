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

    conn.close()

    return render_template(
        "index.html",
        jobs=jobs
    )

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
