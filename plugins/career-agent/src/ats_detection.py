"""ATS platform detection helpers.

Detection can return platforms that are recognized but unsupported for
autonomous apply. Support decisions still live in the apply gates and
confirmation-pattern registry.
"""

from __future__ import annotations

from urllib.parse import urlparse


def detect_ats_platform_from_url(url: str) -> str:
    """Return the recognized ATS platform for a URL, or ``unknown``."""
    if not url:
        return "unknown"

    parsed = urlparse(url.strip())
    host = parsed.netloc.lower()
    if "@" in host:
        host = host.rsplit("@", 1)[1]
    if ":" in host:
        host = host.split(":", 1)[0]

    if host == "job-boards.eu.greenhouse.io":
        return "greenhouse_eu"
    if host == "greenhouse.io" or host.endswith(".greenhouse.io"):
        return "greenhouse"
    if host in {"jobs.lever.co", "jobs.eu.lever.co"} or host.endswith(
        (".jobs.lever.co", ".jobs.eu.lever.co")
    ):
        return "lever"
    if host == "apply.workable.com" or host.endswith(".apply.workable.com"):
        return "workable"
    if host == "jobs.ashbyhq.com":
        return "ashby"
    if host == "teamtailor.com" or host.endswith(".teamtailor.com"):
        return "teamtailor"
    if host == "jobs.personio.com" or host.endswith(".jobs.personio.com"):
        return "personio"

    return "unknown"
