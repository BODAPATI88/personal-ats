import os
from datetime import datetime
from flask import Flask, render_template, request, redirect
from db_utils import fetch_one, fetch_all, execute_query

app = Flask(__name__)

# Status grouping for the dashboard's View Filter (Active Jobs /
# Applications / All Jobs). Mirrors scripts/dashboard.py's
# SUBMITTED_STATUSES - keep in sync if the status enum ever changes.
ACTIVE_STATUSES = ["NEW"]
APPLICATION_STATUSES = ["APPLIED", "HR_ROUND", "TECHNICAL", "FINAL", "OFFER", "REJECTED"]
VIEW_FILTERS = {"active", "applications", "all"}

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
    view = request.args.get("view", "")
    if view not in VIEW_FILTERS:
        # Default dashboard view: active jobs only (Requirement 1).
        view = "active"

    # Job list + overview counts: same base queries as before, now with
    # a status WHERE clause actually applied (this was previously read
    # from the query string but never used - see Priority 6).
    #
    # A specific `status` selection (from the granular Status Filter
    # dropdown) takes precedence over the broader `view` tab, since
    # it's the more specific filter. With no status selected, the view
    # tab determines which statuses are shown.
    conditions = []
    params = []

    if search:
        conditions.append("(title LIKE ? OR company LIKE ?)")
        params += [f"%{search}%", f"%{search}%"]

    if status:
        conditions.append("status = ?")
        params.append(status)
    elif view == "active":
        placeholders = ",".join("?" * len(ACTIVE_STATUSES))
        conditions.append(f"status IN ({placeholders})")
        params += ACTIVE_STATUSES
    elif view == "applications":
        placeholders = ",".join("?" * len(APPLICATION_STATUSES))
        conditions.append(f"status IN ({placeholders})")
        params += APPLICATION_STATUSES
    # view == "all": no status condition - every job, including EXPIRED.

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    jobs = fetch_all(f"""
    SELECT id,title,company,location,status
    FROM jobs
    {where_clause}
    ORDER BY score DESC, id DESC
    """, tuple(params))

    total_jobs = fetch_one("SELECT COUNT(*) FROM jobs")[0]
    applied_jobs = fetch_one("SELECT COUNT(*) FROM jobs WHERE UPPER(status)='APPLIED'")[0]
    new_jobs = fetch_one("SELECT COUNT(*) FROM jobs WHERE UPPER(status)='NEW'")[0]
    offer_jobs = fetch_one("SELECT COUNT(*) FROM jobs WHERE UPPER(status)='OFFER'")[0]

    active_jobs = fetch_one(
        "SELECT COUNT(*) FROM jobs WHERE validation_status='ACTIVE'"
    )[0]

    suspect_jobs = fetch_one(
        "SELECT COUNT(*) FROM jobs WHERE validation_status='SUSPECT'"
    )[0]

    unvalidated_jobs = fetch_one(
        "SELECT COUNT(*) FROM jobs WHERE status='NEW' AND validation_status IS NULL"
    )[0]

    expired_jobs = fetch_one(
        "SELECT COUNT(*) FROM jobs WHERE validation_status='EXPIRED'"
    )[0]

    quality_score = fetch_one("""
SELECT ROUND(
100.0 *
SUM(CASE WHEN validation_status='ACTIVE' THEN 1 ELSE 0 END)
/
SUM(CASE WHEN status='NEW' THEN 1 ELSE 0 END)
,2)
FROM jobs
""")[0]

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
        active_jobs=active_jobs,
        suspect_jobs=suspect_jobs,
        unvalidated_jobs=unvalidated_jobs,
        expired_jobs=expired_jobs,
        quality_score=quality_score,
        search=search,
        status=status,
        view=view,
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
    if new_status == "EXPIRED":
        execute_query(
            "UPDATE jobs SET status=?, expired_at=? WHERE id=?",
            (new_status, datetime.now().isoformat(timespec="seconds"), job_id),
        )
    else:
        # Clear expired_at if a job is being moved off EXPIRED (e.g. a
        # manual correction). No-op for jobs that were never expired.
        execute_query(
            "UPDATE jobs SET status=?, expired_at=NULL WHERE id=?",
            (new_status, job_id),
        )
    return redirect(f"/job/{job_id}")


@app.route("/mark_expired/<int:job_id>", methods=["POST"])
def mark_expired(job_id):
    """Manual 'Mark as Expired' action on the Job Detail page - a
    one-click shortcut for the same EXPIRED transition update_status
    handles, for jobs the automated validator hasn't caught yet."""
    execute_query(
        "UPDATE jobs SET status='EXPIRED', expired_at=? WHERE id=?",
        (datetime.now().isoformat(timespec="seconds"), job_id),
    )
    return redirect(f"/job/{job_id}")

@app.route("/delete/<int:job_id>", methods=["POST"])
def delete_job(job_id):
    execute_query("DELETE FROM jobs WHERE id = ?", (job_id,))
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
