"""Single source of truth for the current ATS release version.

Imported by dashboard.py (and any future script/report that needs to
display which release it's running) so the version string only has to
be updated in one place per release.
"""

ATS_VERSION = "1.4.0"
