# ATS URL Sanitization

**Version:** 1.0.0
**Sprint:** ATS-004

---

## Overview

Gemini API returns URLs in citation format rather than raw strings. Without
sanitization, these values fail scheme validation in Validation Framework v2.0
and are classified as Failures instead of being validated. The sanitization
module normalizes all URL formats to a raw `https://...` string before any
value reaches the database.

---

## Supported Input Formats

| Format | Example | Result |
|--------|---------|--------|
| Raw URL | `https://example.com` | `https://example.com` |
| Whitespace-padded | `  https://example.com  ` | `https://example.com` |
| Gemini citation | `"https://example.com" (https://example.com)` | `https://example.com` |
| Text citation | `"Apply Here" (https://example.com)` | `https://example.com` |
| Markdown link | `[Apply Here](https://example.com)` | `https://example.com` |
| Angle bracket | `<https://example.com>` | `https://example.com` |

---

## Rejection Rules

| Input | Reason |
|-------|--------|
| `ftp://example.com` | Invalid scheme — only `http` and `https` accepted |
| `javascript:alert(1)` | Script injection |
| `""` | Empty string |
| `"   "` | Whitespace-only input |
| `"Apply here"` | No extractable URL found |
| `"https://"` | Empty netloc after parse |
| `"https://exam ple.com"` | Embedded whitespace in URL body |

---

## Sanitization Algorithm

Patterns are evaluated in order. First match wins.

```
1. Strip outer whitespace from input
2. Reject if empty after strip
3. Try: "text" (url)     → extract URL from parentheses
4. Try: [text](url)      → extract URL from parentheses
5. Try: <url>            → extract URL from angle brackets
6. Try: raw http(s):// URL
7. All patterns exhausted → return None

After extraction, validate candidate URL:
  - Strip whitespace
  - Reject embedded whitespace in URL body
  - Reject if "javascript:" appears anywhere in the string
  - Parse with urllib.parse.urlparse
  - Scheme must be "http" or "https"
  - netloc must be non-empty
  - Return candidate on pass, None on any failure
```

---

## Import Pipeline Integration

Sanitization runs in `import_jobs_json.py` **before** duplicate detection.

**Required flow:**
```
Read job from JSON
  → sanitize(job_url)
    → Duplicate detection  ← uses sanitized URL
      → INSERT into jobs   ← stores sanitized URL
```

**Why sanitize before duplicate detection:**
`"https://wipro.com" (https://wipro.com)` and `https://wipro.com` must resolve
to the same value before the duplicate check runs. Without sanitization, both
strings are treated as different URLs and the same job is imported twice.

**Integration pattern in import_jobs_json.py:**

```python
# Add near the top of import_jobs_json.py:
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.url_sanitizer import sanitize

# Where job_url is read from the JSON record, before duplicate detection:
# Replace: job_url = record.get("job_url") or record.get("url") or ""
# With:    job_url = sanitize(record.get("job_url") or record.get("url")) or ""
```

The field name (`"job_url"`, `"url"`) must match what your JSON records
actually contain. Verify from `import_jobs_json.py` source before applying.

---

## Historical Cleanup

Use `fix_markdown_urls.py` to repair malformed URLs already stored in the
database before this sprint was deployed.

### Dry Run (preview — no database writes)

```bash
cd ~/projects/personal-ats
python3 scripts/fix_markdown_urls.py --dry-run
```

Expected output:
```
Scanned: 105
Malformed Found: 4
Would Correct: 4
Would Fail: 0
```

### Live Run

```bash
python3 scripts/fix_markdown_urls.py
echo "Exit: $?"
```

Exit codes:
- `0` — All malformed URLs corrected, or none found
- `1` — One or more URLs could not be extracted (check report)
- `2` — Fatal startup or database error

### After Cleanup

Repaired rows have `validation_status=NULL` and `validated_at=NULL`.
They must be revalidated before they reappear in the Apply Queue.

```bash
python3 scripts/validate_job_urls.py
echo "Exit: $?"
```

---

## Verification Commands

**Count malformed URLs before cleanup:**
```sql
SELECT COUNT(*)
FROM   jobs
WHERE  job_url IS NOT NULL
AND    LOWER(job_url) NOT LIKE 'http://%'
AND    LOWER(job_url) NOT LIKE 'https://%';
```
Expected before cleanup: 4

**Confirm zero malformed URLs after cleanup:**
```sql
SELECT COUNT(*)
FROM   jobs
WHERE  job_url IS NOT NULL
AND    LOWER(job_url) NOT LIKE 'http://%'
AND    LOWER(job_url) NOT LIKE 'https://%';
```
Expected after cleanup: 0

**Verify repaired rows have reset validation metadata:**
```sql
SELECT id, job_url, status, validation_status, validated_at, expired_at
FROM   jobs
WHERE  validation_status IS NULL
AND    validated_at      IS NULL
AND    job_url           IS NOT NULL
AND    LOWER(job_url)    LIKE 'http%';
```
Expected: repaired rows appear with clean URLs and NULL validation fields.

**Verify repaired NEW rows are ready for revalidation:**
```sql
SELECT COUNT(*) AS ready_for_revalidation
FROM   jobs
WHERE  status            = 'NEW'
AND    validation_status IS NULL
AND    job_url           IS NOT NULL
AND    LOWER(job_url)    LIKE 'http%';
```
Expected: matches the corrected count from the cleanup report.

---

## Recovery Procedure

If the cleanup produces unexpected results, restore from the pre-sprint backup:

```bash
cp database/ats.db.bak.<timestamp> database/ats.db
```

The cleanup script is idempotent. Re-running on a partially cleaned database
is safe — already-correct rows are excluded by the query scope and will not
be modified.

---

## Known Limitations

| Limitation | Impact |
|-----------|--------|
| URLs containing `)` in the path may not extract correctly from citation formats | Rare for job board URLs; if encountered, report the raw value for manual correction |
| Sanitizer cannot execute JavaScript | SPA-rendered job boards remain subject to the urllib architectural constraint documented in the Validation Framework |

---

## Files

| File | Purpose |
|------|---------|
| `utils/url_sanitizer.py` | Shared sanitization module |
| `scripts/fix_markdown_urls.py` | One-time historical cleanup |
| `scripts/import_jobs_json.py` | Import pipeline (modified to sanitize before insert) |
| `docs/url-sanitization.md` | This document |
