"""ATS Dashboard - v1.4

Terminal dashboard summarizing pipeline health, top opportunities,
recommendations, company insights, skills gap, and system health.

Renders with the Rich library when it's installed for a nicer terminal
UI; falls back to plain-text tables with zero extra dependencies when
Rich isn't available, so the dashboard always works.

Usage:
    python3 scripts/dashboard.py
"""

import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from version import ATS_VERSION

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

DB_PATH = "database/ats.db"
REPORTS_DIR = Path("reports")

PIPELINE_STATUSES = [
    "NEW",
    "APPLIED",
    "HR_ROUND",
    "TECHNICAL",
    "FINAL",
    "OFFER",
    "REJECTED",
]

# Statuses that count as "an application was submitted" for the
# success-rate calculation in the overview section.
SUBMITTED_STATUSES = ["APPLIED", "HR_ROUND", "TECHNICAL", "FINAL", "OFFER", "REJECTED"]

DAILY_REPORTS = [
    "today_apply_queue.txt",
    "today_recommendations.txt",
    "skills_gap_report.txt",
]

# A company needs at least this many tracked jobs before it's eligible
# for "Top Target Companies" (avg-score ranking). Without this floor, a
# single 100-scored posting could outrank a company with many
# consistently strong matches.
MIN_JOBS_FOR_TARGET_COMPANY = 3


def get_current_branch():
    """Best-effort current git branch name; 'unknown' if git isn't available."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0:
            return result.stdout.strip() or "unknown"
    except Exception:
        pass
    return "unknown"


def connect():
    if not os.path.exists(DB_PATH):
        print(f"Error: database not found at {DB_PATH}")
        print("Run the app once or restore from database/backups/ first.")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)


# ---------------------------------------------------------------------------
# Data gathering
# ---------------------------------------------------------------------------

def fetch_overview(conn):
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM jobs")
    total_jobs = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM jobs WHERE UPPER(status)='NEW'")
    new_jobs = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM jobs WHERE UPPER(status)='APPLIED'")
    applied_jobs = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM jobs WHERE UPPER(status)='OFFER'")
    offer_jobs = cur.fetchone()[0]

    placeholders = ",".join("?" * len(SUBMITTED_STATUSES))
    cur.execute(
        f"SELECT COUNT(*) FROM jobs WHERE UPPER(status) IN ({placeholders})",
        SUBMITTED_STATUSES,
    )
    submitted = cur.fetchone()[0]

    # Success rate = offers won / applications submitted. Submitted means
    # anything that progressed past NEW (APPLIED through REJECTED).
    success_rate = round((offer_jobs / submitted) * 100, 1) if submitted else 0.0

    return {
        "total_jobs": total_jobs,
        "new_jobs": new_jobs,
        "applied_jobs": applied_jobs,
        "success_rate": success_rate,
    }


def fetch_pipeline(conn):
    cur = conn.cursor()
    counts = {}
    for status in PIPELINE_STATUSES:
        cur.execute("SELECT COUNT(*) FROM jobs WHERE UPPER(status)=?", (status,))
        counts[status] = cur.fetchone()[0]
    return counts


def fetch_top_opportunities(conn, limit=10):
    cur = conn.cursor()
    cur.execute(
        "SELECT score, company, title, location FROM jobs "
        "ORDER BY score DESC, id DESC LIMIT ?",
        (limit,),
    )
    return cur.fetchall()


def fetch_company_insights(conn, limit=5):
    cur = conn.cursor()

    # Top companies by raw job count (volume).
    cur.execute(
        "SELECT company, COUNT(*) as c FROM jobs "
        "WHERE company IS NOT NULL AND TRIM(company) != '' "
        "GROUP BY company ORDER BY c DESC LIMIT ?",
        (limit,),
    )
    top_by_volume = cur.fetchall()

    # "Top target companies" = companies with the highest average score,
    # restricted to a minimum job count (MIN_JOBS_FOR_TARGET_COMPANY) so
    # a single high-scored posting can't outrank a company with many
    # consistently strong matches.
    cur.execute(
        "SELECT company, AVG(score) as avg_score, COUNT(*) as c FROM jobs "
        "WHERE company IS NOT NULL AND TRIM(company) != '' "
        "GROUP BY company HAVING COUNT(*) >= ? "
        "ORDER BY avg_score DESC LIMIT ?",
        (MIN_JOBS_FOR_TARGET_COMPANY, limit),
    )
    top_targets = [(c, round(s or 0, 1), n) for c, s, n in cur.fetchall()]

    return top_by_volume, top_targets


def read_recommendations(limit=8):
    """Top recommended jobs from reports/today_recommendations.txt.

    Returns None if the report hasn't been generated yet.
    """
    path = REPORTS_DIR / "today_recommendations.txt"
    if not path.exists():
        return None

    rows = []
    for line in path.read_text().splitlines():
        parts = line.split("|")
        if len(parts) != 5:
            continue
        _job_id, company, title, score, rec = parts
        rows.append((company, title, score, rec))

    return rows[:limit]


def read_skills_gap(conn):
    """Top missing skills from reports/skills_gap_report.txt, plus the
    average ATS match score (the existing resume-aware `score` column,
    averaged) across currently-tracked NEW jobs.

    Note: this is the average recommendation/match score the scoring
    engine assigns to NEW jobs, not a measure of resume completeness -
    don't relabel it "Resume Match %".

    Returns (missing_skills, avg_match_score, report_exists).
    """
    path = REPORTS_DIR / "skills_gap_report.txt"
    missing = []

    if path.exists():
        in_missing_section = False
        for line in path.read_text().splitlines():
            if line.startswith("Top Missing Skills"):
                in_missing_section = True
                continue
            if line.startswith("Strongest Matching Skills"):
                break
            if in_missing_section and "required in" in line:
                skill_part, _, rest = line.partition("required in")
                missing.append((skill_part.strip(), rest.strip()))

    cur = conn.cursor()
    cur.execute("SELECT AVG(score) FROM jobs WHERE UPPER(status)='NEW'")
    avg_score = cur.fetchone()[0]
    avg_match_score = round(avg_score, 1) if avg_score is not None else None

    return missing[:5], avg_match_score, path.exists()


def report_status(filename):
    """Return a short status string for a generated report file:
    MISSING, OK (generated within the last 24h), or STALE (older).
    """
    path = REPORTS_DIR / filename
    if not path.exists():
        return "MISSING", None

    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    age_hours = (datetime.now() - mtime).total_seconds() / 3600
    label = "OK" if age_hours <= 24 else "STALE"
    return label, mtime.strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------------------------
# Rich rendering
# ---------------------------------------------------------------------------

def render_rich(data):
    console = Console()

    console.print(Panel.fit(f"[bold cyan]Personal ATS Dashboard[/bold cyan]  v{ATS_VERSION}"))

    # A. ATS Overview
    ov = data["overview"]
    overview_table = Table(title="ATS Overview", show_header=False)
    overview_table.add_row("ATS Version", ATS_VERSION)
    overview_table.add_row("Current Branch", data["branch"])
    overview_table.add_row("Total Jobs", str(ov["total_jobs"]))
    overview_table.add_row("New Jobs", str(ov["new_jobs"]))
    overview_table.add_row("Applied Jobs", str(ov["applied_jobs"]))
    overview_table.add_row("Success Rate", f"{ov['success_rate']}%")
    console.print(overview_table)

    # B. Application Pipeline
    pipeline_table = Table(title="Application Pipeline")
    pipeline_table.add_column("Status")
    pipeline_table.add_column("Count", justify="right")
    for status, count in data["pipeline"].items():
        pipeline_table.add_row(status, str(count))
    console.print(pipeline_table)

    # C. Top Opportunities
    top_table = Table(title="Top Opportunities (Top 10)")
    top_table.add_column("Score", justify="right")
    top_table.add_column("Company")
    top_table.add_column("Role")
    top_table.add_column("Location")
    for score, company, title, location in data["top_opportunities"]:
        top_table.add_row(str(score), company or "-", title or "-", location or "-")
    console.print(top_table)

    # D. Today's Recommended Applications
    rec_table = Table(title="Today's Recommended Applications")
    if data["recommendations"] is None:
        console.print(
            "[yellow]No recommendations yet. Run scripts/recommend_jobs.py.[/yellow]"
        )
    else:
        rec_table.add_column("Company")
        rec_table.add_column("Role")
        rec_table.add_column("Score", justify="right")
        rec_table.add_column("Recommendation")
        for company, title, score, rec in data["recommendations"]:
            rec_table.add_row(company, title, score, rec)
        console.print(rec_table)

    # E. Company Insights
    by_volume, top_targets = data["company_insights"]

    volume_table = Table(title="Top Companies by Job Count")
    volume_table.add_column("Company")
    volume_table.add_column("Jobs", justify="right")
    for company, count in by_volume:
        volume_table.add_row(company, str(count))
    console.print(volume_table)

    target_table = Table(title=f"Top Target Companies (min {MIN_JOBS_FOR_TARGET_COMPANY} jobs)")
    target_table.add_column("Company")
    target_table.add_column("Avg Score", justify="right")
    target_table.add_column("Jobs", justify="right")
    for company, avg_score, count in top_targets:
        target_table.add_row(company, str(avg_score), str(count))
    console.print(target_table)
    if not top_targets:
        console.print(
            f"[yellow]No company has {MIN_JOBS_FOR_TARGET_COMPANY}+ tracked jobs yet.[/yellow]"
        )

    # F. Skills Gap Summary
    missing, avg_match_score, exists = data["skills_gap"]
    match_str = f"{avg_match_score}%" if avg_match_score is not None else "N/A"
    console.print(f"[bold]Skills Gap Summary[/bold]  (Average ATS Match Score: {match_str})")
    if not exists:
        console.print("[yellow]No skills gap report yet. Run scripts/skills_gap_report.py.[/yellow]")
    elif not missing:
        console.print("Resume covers all tracked job requirements.")
    else:
        gap_table = Table(show_header=True)
        gap_table.add_column("Missing Skill")
        gap_table.add_column("Demand")
        for skill, demand in missing:
            gap_table.add_row(skill, demand)
        console.print(gap_table)

    # G. System Health
    health = data["system_health"]
    health_table = Table(title="System Health", show_header=False)
    health_table.add_column("Field")
    health_table.add_column("Value", overflow="fold")
    health_table.add_row("Database Path", health["db_path"])
    health_table.add_row("Job Count", str(health["job_count"]))
    for filename, (label, ts) in health["report_status"].items():
        display = label if ts is None else f"{label} ({ts})"
        health_table.add_row(f"Report: {filename}", display)
    console.print(health_table)


# ---------------------------------------------------------------------------
# Plain-text rendering (no dependencies)
# ---------------------------------------------------------------------------

def section_header(title):
    print()
    print(title)
    print("-" * max(len(title), 40))


def render_plain(data):
    print("=" * 50)
    print(f"PERSONAL ATS DASHBOARD - v{ATS_VERSION}")
    print("=" * 50)

    # A. ATS Overview
    ov = data["overview"]
    section_header("A. ATS OVERVIEW")
    print(f"ATS Version     : {ATS_VERSION}")
    print(f"Current Branch  : {data['branch']}")
    print(f"Total Jobs      : {ov['total_jobs']}")
    print(f"New Jobs        : {ov['new_jobs']}")
    print(f"Applied Jobs    : {ov['applied_jobs']}")
    print(f"Success Rate    : {ov['success_rate']}%")

    # B. Application Pipeline
    section_header("B. APPLICATION PIPELINE")
    for status, count in data["pipeline"].items():
        print(f"{status:<12}: {count}")

    # C. Top Opportunities
    section_header("C. TOP OPPORTUNITIES (Top 10)")
    if not data["top_opportunities"]:
        print("No jobs tracked yet.")
    for score, company, title, location in data["top_opportunities"]:
        print(f"{score:>6} | {company or '-':<25} | {title or '-':<35} | {location or '-'}")

    # D. Today's Recommended Applications
    section_header("D. TODAY'S RECOMMENDED APPLICATIONS")
    if data["recommendations"] is None:
        print("No recommendations yet. Run scripts/recommend_jobs.py.")
    elif not data["recommendations"]:
        print("No NEW jobs to recommend.")
    else:
        for company, title, score, rec in data["recommendations"]:
            print(f"{company:<25} | {title:<35} | {score:>6} | {rec}")

    # E. Company Insights
    section_header("E. COMPANY INSIGHTS")
    by_volume, top_targets = data["company_insights"]
    print("Top Companies by Job Count:")
    for company, count in by_volume:
        print(f"  {company:<30}: {count}")
    print(f"\nTop Target Companies (min {MIN_JOBS_FOR_TARGET_COMPANY} jobs):")
    if not top_targets:
        print(f"  No company has {MIN_JOBS_FOR_TARGET_COMPANY}+ tracked jobs yet.")
    for company, avg_score, count in top_targets:
        print(f"  {company:<30}: avg score {avg_score} ({count} jobs)")

    # F. Skills Gap Summary
    section_header("F. SKILLS GAP SUMMARY")
    missing, avg_match_score, exists = data["skills_gap"]
    match_str = f"{avg_match_score}%" if avg_match_score is not None else "N/A"
    print(f"Average ATS Match Score (NEW jobs): {match_str}")
    if not exists:
        print("No skills gap report yet. Run scripts/skills_gap_report.py.")
    elif not missing:
        print("Resume covers all tracked job requirements.")
    else:
        for skill, demand in missing:
            print(f"  {skill:<25} required in {demand}")

    # G. System Health
    section_header("G. SYSTEM HEALTH")
    health = data["system_health"]
    print(f"Database Path : {health['db_path']}")
    print(f"Job Count     : {health['job_count']}")
    print("Report Status :")
    for filename, (label, ts) in health["report_status"].items():
        display = label if ts is None else f"{label} ({ts})"
        print(f"  {filename:<30}: {display}")

    print()
    print("=" * 50)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def gather_data(conn):
    db_path = os.path.abspath(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM jobs")
    job_count = cur.fetchone()[0]

    return {
        "branch": get_current_branch(),
        "overview": fetch_overview(conn),
        "pipeline": fetch_pipeline(conn),
        "top_opportunities": fetch_top_opportunities(conn),
        "recommendations": read_recommendations(),
        "company_insights": fetch_company_insights(conn),
        "skills_gap": read_skills_gap(conn),
        "system_health": {
            "db_path": db_path,
            "job_count": job_count,
            "report_status": {name: report_status(name) for name in DAILY_REPORTS},
        },
    }


def main():
    conn = connect()
    try:
        try:
            data = gather_data(conn)
        except sqlite3.OperationalError as e:
            print(f"Error reading database: {e}")
            print("If this is a fresh database, run scripts/migrate_db.py first.")
            sys.exit(1)
    finally:
        conn.close()

    if RICH_AVAILABLE:
        render_rich(data)
    else:
        render_plain(data)


if __name__ == "__main__":
    main()
