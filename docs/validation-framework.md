ATS Validation Framework
Version: 2.0.0
Sprint: ATS Automation & Data Quality
Branch: feature/ats-validation-framework
Overview
The Validation Framework introduces a three-state URL validation layer between
job ingestion and the Apply Queue. Prior to this framework, all inconclusive
validation outcomes (timeouts, bot-blocks, network errors) left jobs in
status='NEW', making them indistinguishable from genuinely live listings.
The framework separates validation state (validation_status) from workflow
lifecycle (status). The Apply Queue now requires both conditions:
Sql
Status Definitions
ACTIVE
No negative signal detected in the raw HTTP response.
Trigger conditions:
HTTP 200
No closed phrase matched in response body
No CAPTCHA/anti-bot phrase detected
Semantic limitation: ACTIVE means no evidence of closure found, not
confirmed live. urllib cannot execute JavaScript. SPA-rendered job boards
(LinkedIn, Naukri, Workday, Taleo) may return HTTP 200 with an empty HTML shell
even after a listing has closed. Those listings are classified ACTIVE by this
implementation. This is an architectural constraint of the current
implementation, not a defect. See Known Limitations.
SUSPECT
Validation inconclusive. Excluded from Apply Queue. Retained for review.
Trigger conditions:
HTTP 403 (bot-blocked)
HTTP 429 (rate-limited)
Timeout (> 5 seconds)
Network error / URLError
CAPTCHA/anti-bot phrase detected in response body
Any HTTP status code not covered by ACTIVE or EXPIRED rules
Design intent: False negatives (missing live jobs) are preferred over
false expiration. SUSPECT is the conservative outcome for any uncertain signal.
Per CTO Decision 3: when CAPTCHA and closed phrases both appear in a response,
SUSPECT takes precedence over EXPIRED.
EXPIRED
Definitively dead listing. Excluded from Apply Queue.
Trigger conditions:
HTTP 404
HTTP 410
Closed phrase matched in response body:
"job no longer available"
"position filled"
"posting removed"
"vacancy closed"
"no longer accepting applications"
Database Schema Changes
New Columns
Column
Type
Purpose
validation_status
TEXT
ACTIVE | SUSPECT | EXPIRED | NULL
validated_at
TEXT
ISO 8601 timestamp of most recent validation attempt
NULL in validation_status means the job has never been validated under this
framework. It is distinct from SUSPECT.
Retained Columns (unchanged behaviour)
Column
Behaviour
status
Lifecycle field. EXPIRED writes still set status='EXPIRED'

for backward compatibility.
expired_at
Populated only when validation_status='EXPIRED'.

Behaviour unchanged from v1.5.1.
Apply Queue Filter
Before:
Sql
After:
Sql
Files Changed
File
Change
scripts/migrate_validation_framework.py
CREATE
scripts/validate_job_urls.py
MODIFY
scripts/recommend_jobs.py
MODIFY
scripts/generate_apply_queue.py
MODIFY
docs/validation-framework.md
CREATE
Known Limitations
#
Limitation
Impact
Resolution Path
L1
urllib cannot execute JavaScript
SPA boards (LinkedIn, Naukri, Workday, Taleo) may classify closed listings as ACTIVE
Playwright/Selenium — deferred to future sprint
L2
Redirect detection not implemented
Homepage-redirecting expired listings may classify as ACTIVE
Deferred after Phase 1 production data review
L3
Apply CTA detection not implemented
Absence of apply button not detected
Board-specific HTML parsing — deferred
L4
CAPTCHA inflation under concurrent load
MAX_CONCURRENT=10 may trigger per-domain rate limits, producing SUSPECT inflation
Domain-aware throttling — deferred
Operational Notes
Running the Validator
Bash
Exit codes:
Code
Meaning
0
Validation completed, zero job-level failures
1
Validation completed, one or more failures
2
Fatal — database unavailable or startup error
Checking Validation State
Bash
Reading the Report
Bash
Reading the Log
Bash
Log entries are newline-delimited JSON. One entry per run:
Json
Report arithmetic:
Code
Deployment Sequence
Do not deviate from this sequence. Switching recommendation filters before
Step 4 produces an empty Apply Queue.
Code
Rollback
Code Rollback (all SQLite versions)
Bash
After code rollback, the Apply Queue reverts to WHERE status='NEW'. Jobs
with validation_status='SUSPECT' re-enter the queue. This is expected
behaviour — it is the pre-framework state.
Schema Rollback (SQLite >= 3.35.0 only)
Bash
Database Restore (any SQLite version)
Bash
If SQLite < 3.35.0, use database restore. Code rollback alone is sufficient
for Apply Queue protection — the old filter ignores the new columns.
Release Notes — v2.0.0
Introduced three-state validation: ACTIVE, SUSPECT, EXPIRED
SUSPECT now written for bot-blocks, timeouts, CAPTCHA pages (previously
silently left as NEW)
Apply Queue hardened: only validation_status='ACTIVE' eligible
Added validation_status and validated_at columns to jobs table
Structured JSON logging added to ats.log (one line per run)
Validation report expanded: ACTIVE/SUSPECT/EXPIRED/Skipped/Failures
Exit codes: 0 (success), 1 (partial), 2 (fatal)
Migration idempotent: safe to run multiple times
urllib architectural limitation documented: ACTIVE = no negative signal
detected, not confirmed live
