from flask import Flask, render_template, request, redirect
from db_utils import fetch_one, fetch_all, execute_query

app = Flask(__name__)

@app.route("/")
def home():

    search = request.args.get("search", "")
    status = request.args.get("status", "")

    conn = sqlite3.connect("database/ats.db")
    cursor = conn.cursor()

    if search:
        cursor.execute("""
        SELECT id,title,company,location,status
        FROM jobs
        WHERE title LIKE ? OR company LIKE ?
        ORDER BY id DESC
        """, (f"%{search}%", f"%{search}%"))
    else:
        cursor.execute("""
        SELECT id,title,company,location,status
        FROM jobs
        ORDER BY id DESC
        """)

    jobs = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM jobs")
    total_jobs = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM jobs WHERE UPPER(status)='APPLIED'")
    applied_jobs = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM jobs WHERE UPPER(status)='NEW'")
    new_jobs = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM jobs WHERE UPPER(status)='OFFER'")
    offer_jobs = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "index.html",
        jobs=jobs,
        total_jobs=total_jobs,
        applied_jobs=applied_jobs,
        new_jobs=new_jobs,
        offer_jobs=offer_jobs,
        search=search
    )

@app.route("/add_job", methods=["GET","POST"])
def add_job():

    if request.method == "POST":
        title = request.form["title"]
        company = request.form["company"]
        location = request.form["location"]
        execute_query("INSERT INTO jobs (title, company, location) VALUES (?, ?, ?)", (title, company, location))

        return redirect("/")

    return render_template("add_job.html")

@app.route("/job/<int:job_id>")
def job_detail(job_id):
    job = fetch_one("SELECT * FROM jobs WHERE id = ?", (job_id,))
    if job is None:
        return "Job not found", 404
    return render_template("job_detail.html", job=job)


@app.route("/edit/<int:job_id>", methods=["GET","POST"])
def edit_job(job_id):
    if request.method == "POST":
        title = request.form["title"]
        company = request.form["company"]
        location = request.form["location"]
        status = request.form["status"]
        execute_query("UPDATE jobs SET title=?, company=?, location=?, status=? WHERE id=?", (title, company, location, status, job_id))
        return redirect(f"/job/{job_id}")

    job = fetch_one("SELECT * FROM jobs WHERE id = ?", (job_id,))

    if job is None:
        return "Job not found", 404

    return render_template("edit_job.html", job=job)

@app.route("/update_status/<int:job_id>", methods=["POST"])
def update_status(job_id):
    new_status = request.form["status"]
    execute_query("UPDATE jobs SET status = ? WHERE id = ?", (new_status, job_id))
    return redirect(f"/job/{job_id}")

@app.route("/delete/<int:job_id>", methods=["POST"])
def delete_job(job_id):
    execute_query("DELETE FROM jobs WHERE id = ?", (job_id,))
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
