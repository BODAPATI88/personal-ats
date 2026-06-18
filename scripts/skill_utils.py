"""Shared resume & skill matching helpers.

Used by score_jobs.py (resume-aware scoring) and skills_gap_report.py
(skills gap analysis) so both stay consistent about how resume skills
are loaded and how a job's required skills are matched against them.
"""

from pathlib import Path

RESUME_SKILLS_FILE = Path(__file__).resolve().parent.parent / "resume" / "ravi_resume.txt"

# Importance weights used when scoring how well a job matches the resume.
# Skills not listed here fall back to BASE_WEIGHT. These mirror the
# original keyword weights from the legacy title-only scorer, extended
# to apply to any matched skill rather than just title substrings.
SKILL_WEIGHTS = {
    "kubernetes": 25,
    "azure": 20,
    "terraform": 15,
    "devops": 15,
    "platform": 10,
    "platform engineering": 10,
    "site reliability": 10,
    "sre": 10,
    "cloud": 5,
    "linux": 5,
}
BASE_WEIGHT = 5


def normalize(skill):
    return skill.strip().lower()


def load_resume_skills(path=RESUME_SKILLS_FILE):
    """Load the resume's skill list as a normalized set of strings."""
    if not path.exists():
        return set()

    return {
        normalize(line)
        for line in path.read_text().splitlines()
        if line.strip()
    }


def parse_job_skills(skills_field, title=""):
    """Return the list of skills required for a job.

    Prefers the explicit `skills` column (populated from the fetcher's
    primary_skills field on import). Falls back to scanning the job
    title for known weighted keywords when no structured skill data
    exists yet (e.g. jobs imported from jobs.csv before this column
    existed, or rows added before a re-import).
    """
    if skills_field:
        return [normalize(s) for s in skills_field.split(",") if s.strip()]

    title_lower = (title or "").lower()
    return [kw for kw in SKILL_WEIGHTS if kw in title_lower]


def weighted_match(job_skills, resume_skills):
    """Compute a 0-100 weighted match score plus matched/missing skills.

    Each required skill contributes its weight to the total; matched
    skills (present in the resume) contribute their weight to the
    score. This keeps higher-priority skills (e.g. Kubernetes) more
    influential than minor ones, while being driven by the actual
    resume contents rather than a fixed title-keyword check.
    """
    if not job_skills:
        return 0.0, [], []

    matched, missing = [], []
    matched_weight = 0
    total_weight = 0

    for skill in job_skills:
        weight = SKILL_WEIGHTS.get(skill, BASE_WEIGHT)
        total_weight += weight
        if skill in resume_skills:
            matched.append(skill)
            matched_weight += weight
        else:
            missing.append(skill)

    score = round((matched_weight / total_weight) * 100, 1) if total_weight else 0.0
    return min(score, 100.0), sorted(matched), sorted(missing)
