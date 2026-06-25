"""URL Sanitization Utility - v1.0.0

Extracts and normalizes job URLs from various input formats produced by
Gemini API output, Markdown links, and direct URL entry.

Public interface:
    sanitize(url) -> Optional[str]

    Returns normalized URL string on success.
    Returns None for invalid input, unrecognised format, or rejected scheme.
    Never raises.

Accepted input formats:
    Raw URL           https://example.com
    Whitespace-padded " https://example.com "
    Gemini citation   "https://example.com" (https://example.com)
    Text citation     "Apply Here" (https://example.com)
    Markdown link     [Apply Here](https://example.com)
    Angle bracket     <https://example.com>

Rejected inputs (returns None):
    Invalid scheme    ftp://example.com
    Script injection  javascript:alert(1)
    Empty/whitespace  "", "   "
    No URL present    "Apply here"
    Empty netloc      "https://"
    Embedded spaces   "https://exam ple.com"
"""

import re
from typing import Optional
import urllib.parse


ALLOWED_SCHEMES = frozenset({"http", "https"})


# ── Extraction patterns (evaluated in order; first match wins) ────────────────

# Gemini citation and text citation: "text" (url)
# Matches both:
#   "https://example.com" (https://example.com)   [Gemini citation]
#   "Apply Here" (https://example.com)             [text citation]
# URL is always extracted from the parenthesised segment.
_RE_QUOTED_PAREN = re.compile(
    r'^"[^"]*"\s*\((https?://[^)]+)\)\s*$',
    re.IGNORECASE,
)

# Standard Markdown link: [text](url)
_RE_MARKDOWN_LINK = re.compile(
    r'^\[.*?\]\((https?://[^)]+)\)\s*$',
    re.IGNORECASE,
)

# Angle bracket URL: <url>
_RE_ANGLE_BRACKET = re.compile(
    r'^<(https?://[^>]+)>\s*$',
    re.IGNORECASE,
)

_PATTERNS = (_RE_QUOTED_PAREN, _RE_MARKDOWN_LINK, _RE_ANGLE_BRACKET)


def sanitize(url: Optional[str]) -> Optional[str]:
    """Extract and validate a URL from various input formats.

    Returns normalized URL string on success.
    Returns None for any invalid, unrecognised, or rejected input.
    Never raises; exceptions are caught and treated as None return.
    """
    if url is None:
        return None
    try:
        return _extract_and_validate(url)
    except Exception:
        return None


def _extract_and_validate(raw: str) -> Optional[str]:
    """Internal implementation. Called by sanitize() which catches all exceptions."""
    value = raw.strip()
    if not value:
        return None

    # Try structured patterns before raw URL check to avoid partial matches
    for pattern in _PATTERNS:
        match = pattern.match(value)
        if match:
            return _validate(match.group(1))

    # Try raw URL (http:// or https://)
    if value.lower().startswith(("http://", "https://")):
        return _validate(value)

    # No pattern matched — unrecognised format
    return None


def _validate(candidate: str) -> Optional[str]:
    """Validate an extracted URL candidate.

    Checks: scheme allowlist, non-empty netloc, no embedded whitespace,
    no javascript: injection. Uses urllib.parse.urlparse for structural
    validation per sprint requirement.

    Returns stripped candidate on success, None on any rejection.
    """
    candidate = candidate.strip()
    if not candidate:
        return None

    # Reject embedded whitespace (space, tab, newline anywhere in the URL)
    if any(c.isspace() for c in candidate):
        return None

    # Reject javascript: injection — checked before urlparse to catch
    # obfuscated forms that urlparse might not recognise as dangerous.
    if "javascript:" in candidate.lower():
        return None

    # Structural validation via urlparse (sprint requirement)
    try:
        parsed = urllib.parse.urlparse(candidate)
    except ValueError:
        return None

    # Scheme must be in allowlist (rejects ftp://, data:, etc.)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        return None

    # netloc must be non-empty (rejects bare scheme: "https://")
    if not parsed.netloc:
        return None

    return candidate
