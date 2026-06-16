#!/bin/bash

python3 scripts/import_jobs_json.py imports/jobs/jobs_$(date +%Y_%m_%d).json
python3 scripts/score_jobs.py
