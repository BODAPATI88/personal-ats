#!/bin/bash
set -e

FILE="imports/jobs/jobs_$(date +%Y_%m_%d).json"

if [ -f "$FILE" ]; then
    python3 scripts/import_jobs_json.py "$FILE"
fi

python3 scripts/score_jobs.py
python3 scripts/skills_gap_report.py
python3 scripts/recommend_jobs.py
python3 scripts/generate_apply_queue.py
