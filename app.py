import os
from flask import Flask, render_template, request, redirect
from db_utils import fetch_one, fetch_all, execute_query

app = Flask(__name__)

# Reports directory written by the existing v1.4 report scripts
# (scripts/application_pipeline_report.py, recommend_jobs.py,
# generate_apply_queue.py, top_companies_report.py). This route only
# reads those files - it never writes to reports/ or recomputes
# scores/recommendations itself.
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")


def _read_report(filename):
    """Return the raw text of a report file, or None if it hasn't been generated yet."""
    path = os.path.join(REPORTS_DIR, filename)
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return f.read()


def parse_pipeline_report():
    """Parse reports/application_pipeline.txt (written by
    scripts/application_pipeline_report.py) into a summary dict and a
    list of {status, count} breakdown rows."""
    content = _read_report("application_pipeline.txt")
    result = {"available": False, "summary": {}, "breakdown": []}
    if not content:
        return result

    result["available"] = True
    in_breakdown = False
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line == "Pipeline Breakdown:":
            in_breakdown = True
            continue
        if line.startswith("=") or line.endswith("Report"):
            continue
        if in_breakdown:
            if ":" in line:
                status, count = line.split(":", 1)
                result["breakdown"].append({"status": status.strip(), "count": count.strip()})
        elif ":" in line:
            key, value = line.split(":", 1)
            result["summary"][key.strip()] = value.strip()

    return result


def parse_pipe_delimited_report(filename, field_names, limit=None):
    """Parse a pipe-delimited report file (today_recommendations.txt,
    today_apply_queue.txt) into a list of dicts keyed by field_names."""
    content = _read_report(filename)
    if not content:
        return []

    entries = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split("|")
        if len(parts) != len(field_names):
            continue
        entries.append(dict(zip(field_names, parts)))

    if limit:
        entries = entries[:limit]
    return entries


def parse_top_companies_report():
    """Parse reports/top_companies.txt (written by
    scripts/top_companies_report.py) into by-volume and top-target
    company lists."""
    content = _read_report("top_companies.txt")
    result = {"available": False, "by_volume": [], "top_targets": [], "targets_heading": ""}
    if not content:
        return result

    result["available"] = True
    section = None
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("Top Companies by Job Count"):
            section = "volume"
            continue
        if line.startswith("Top Target Companies"):
            section = "targets"
            result["targets_heading"] = line
            continue
        if line.startswith("=") or line.endswith("Report") or line.startswith("Generated At"):
            continue

        if section == "volume" and ":" in line:
            company, count = line.split(":", 1)
            result["by_volume"].append({"company": company.strip(), "count": count.strip()})
        elif section == "targets" and ":" in line:
            company, detail = line.split(":", 1)
            result["top_targets"].append({"company": company.strip(), "detail": detail.strip()})

    # Display cap only - the underlying report has no limit (REPORT_LIMIT
    # in top_companies_report.py), the dashboard just doesn't need every row.
    result["by_volume"] = result["by_volume"][:10]
    return result


@app.route("/")
def home():

    search = request.args.get("search", "")
    status = request.args.get("status", "")

    # Job list + overview counts: same queries as before, just run through
    # db_utils (already used by every other route in this file) instead of
    # a raw sqlite3 connection.
    if search:
        jobs = fetch_all("""
        SELECT id,title,company,location,status
        FROM jobs
        WHERE title LIKE ? OR company LIKE ?
        ORDER BY score DESC, id DESC
        """, (f"%{search}%", f"%{search}%"))
    else:
        jobs = fetch_all("""
        SELECT id,title,company,location,status
        FROM jobs
        ORDER BY score DESC, id DESC
        """)

    total_jobs = fetch_one("SELECT COUNT(*) FROM jobs")[0]
    applied_jobs = fetch_one("SELECT COUNT(*) FROM jobs WHERE UPPER(status)='APPLIED'")[0]
    new_jobs = fetch_one("SELECT COUNT(*) FROM jobs WHERE UPPER(status)='NEW'")[0]
    offer_jobs = fetch_one("SELECT COUNT(*) FROM jobs WHERE UPPER(status)='OFFER'")[0]

    # Dashboard sections 2-5: read-only parsing of existing v1.4 report
    # files under reports/. No scoring, recommendation, or report
    # generation logic lives here - this route never writes to reports/.
    pipeline = parse_pipeline_report()
    recommendations = parse_pipe_delimited_report(
        "today_recommendations.txt",
        ["id", "company", "title", "score", "recommendation"],
        limit=10,
    )
    apply_queue = parse_pipe_delimited_report(
        "today_apply_queue.txt",
        ["id", "title", "company", "score"],
        limit=10,
    )
    companies = parse_top_companies_report()

    return render_template(
        "index.html",
        jobs=jobs,
        total_jobs=total_jobs,
        applied_jobs=applied_jobs,
        new_jobs=new_jobs,
        offer_jobs=offer_jobs,
        search=search,
        pipeline=pipeline,
        recommendations=recommendations,
        apply_queue=apply_queue,
        companies=companies,
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
