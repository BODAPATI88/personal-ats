from pathlib import Path

resume_file = Path("resume/ravi_resume.txt")
jd_file = Path("jobs/sample_jd.txt")

resume_skills = {
    line.strip().lower()
    for line in resume_file.read_text().splitlines()
    if line.strip()
}

jd_skills = {
    line.strip().lower()
    for line in jd_file.read_text().splitlines()
    if line.strip()
}

ignore = {"senior platform engineer", "required skills:"}
jd_skills = jd_skills - ignore

matched = sorted(resume_skills & jd_skills)
missing = sorted(jd_skills - resume_skills)

score = round((len(matched) / len(jd_skills)) * 100, 1)

print("\nATS Match Report")
print("-" * 40)

print(f"Match Score : {score}%")

print("\nMatched Skills:")
for skill in matched:
    print(f"✓ {skill}")

print("\nMissing Skills:")
for skill in missing:
    print(f"✗ {skill}")

print("\nRecommendation:")

if score >= 75:
    print("APPLY")
elif score >= 60:
    print("REVIEW")
else:
    print("SKIP")
