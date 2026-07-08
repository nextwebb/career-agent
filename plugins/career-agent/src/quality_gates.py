"""Deterministic quality gates for generated CV and cover-letter PDFs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

OK = "PASS"
WARN = "WARN"
FAIL = "FAIL"

PLACEHOLDER_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bTODO\b",
        r"\bFIXME\b",
        r"lorem ipsum",
        r"describe your",
        r"bullet\s+\d+",
        r"opening paragraph",
        r"paragraph\s+\d+",
        r"overridden bullet",
        r"specific hook",
        r"fit with this specific JD",
        # Anchored to the literal /new-role template stub
        # ("Paragraph 2: relevant experience, concrete evidence..."). Catches
        # the case where a user trims TODO/Paragraph N/ellipsis anchors but
        # leaves the comma-joined hint phrase intact. Specific enough that it
        # does not collide with normal CV/CL prose.
        r"relevant experience,\s*concrete evidence",
        r"\.\.\.",
    ]
]

WEAK_PHRASES = [
    "hard-working",
    "hardworking",
    "team player",
    "passionate",
    "detail-oriented",
    "go-getter",
    "responsible for",
]

# Numeric evidence signal: a digit, a percentage, or a standalone `x`
# multiplier (e.g. "3x throughput"). Shared by impact_evidence_density
# and per_bullet_result_signal so both gates agree on what counts as
# numeric evidence.
NUMERIC_EVIDENCE_PATTERN = re.compile(r"\d|%|\bx\b")

# Conservative list of scale phrases that describe a measurable change in
# a Result. `improved` alone is intentionally excluded because it does
# not carry a magnitude on its own; require `improved by` instead.
SCALE_PHRASE_PATTERN = re.compile(
    r"\b("
    r"reduced|"
    r"improved by|"
    r"cut|"
    r"increased by|"
    r"saved|"
    r"boosted|"
    r"accelerated|"
    r"optimised|"
    r"optimized"
    r")\b",
    re.IGNORECASE,
)

# Approved metric placeholders left by the author when the concrete
# value is still to be filled in. Case-sensitive on purpose: the
# placeholders are a fixed convention documented in the profile schema
# and lower-case variants like `[~n]` are typos, not signals.
METRIC_PLACEHOLDER_PATTERN = re.compile(r"\[~(?:N|%|€)\]")


@dataclass(frozen=True)
class GateResult:
    """One deterministic quality gate result."""

    status: str
    name: str
    message: str


@dataclass(frozen=True)
class PdfSnapshot:
    """Machine-readable facts extracted from a generated PDF."""

    path: Path
    text: str
    pages: int
    links: tuple[str, ...]
    image_count: int


@dataclass(frozen=True)
class QualityReport:
    """Aggregate gate report for a generated application packet."""

    results: tuple[GateResult, ...]

    @property
    def has_failures(self) -> bool:
        return any(result.status == FAIL for result in self.results)

    @property
    def has_warnings(self) -> bool:
        return any(result.status == WARN for result in self.results)


class QualityGateError(Exception):
    """Raised when quality gates fail in strict command-line execution."""


def _full_name(profile: dict[str, Any]) -> str:
    name = profile.get("name", "")
    if isinstance(name, dict):
        return f"{name.get('first', '')} {name.get('last', '')}".strip()
    return str(name).strip()


def _read_pdf(path: str | Path) -> tuple[PdfSnapshot | None, str | None]:
    try:
        from pypdf import PdfReader
    except ImportError:
        return None, "pypdf is not installed; run `pip install -r requirements.txt`."

    pdf_path = Path(path)
    if not pdf_path.exists():
        return None, f"{pdf_path} does not exist."
    if pdf_path.stat().st_size < 512:
        return None, f"{pdf_path} is too small to be a complete PDF."

    try:
        reader = PdfReader(str(pdf_path))
        text_parts = []
        links: list[str] = []
        image_count = 0

        for page in reader.pages:
            extracted = page.extract_text() or ""
            text_parts.append(extracted)

            annotations = page.get("/Annots") or []
            for annotation_ref in annotations:
                annotation = annotation_ref.get_object()
                action = annotation.get("/A") or {}
                uri = action.get("/URI")
                if uri:
                    links.append(str(uri))

            resources = page.get("/Resources") or {}
            xobjects = resources.get("/XObject") or {}
            for xobject_ref in xobjects.values():
                xobject = xobject_ref.get_object()
                if xobject.get("/Subtype") == "/Image":
                    image_count += 1

        return (
            PdfSnapshot(
                path=pdf_path,
                text="\n".join(text_parts),
                pages=len(reader.pages),
                links=tuple(links),
                image_count=image_count,
            ),
            None,
        )
    except Exception as error:  # pypdf raises several parser-specific exceptions
        return None, f"{pdf_path} could not be parsed as a PDF: {error}"


def _contains_placeholder(text: str) -> list[str]:
    return [pattern.pattern for pattern in PLACEHOLDER_PATTERNS if pattern.search(text)]


def _normalise_lines(values: list[Any]) -> list[str]:
    lines: list[str] = []
    for value in values:
        if isinstance(value, str):
            lines.append(value)
    return [line.strip().lower() for line in lines if line.strip()]


def _experience_bullets(config: dict[str, Any]) -> list[str]:
    bullets: list[str] = []
    for role in config.get("experience", []):
        role_bullets = role.get("bullets", []) if isinstance(role, dict) else []
        if isinstance(role_bullets, list):
            bullets.extend(str(bullet) for bullet in role_bullets if str(bullet).strip())
    return bullets


def _bullet_has_result_signal(bullet: str) -> bool:
    """Return True when a bullet carries a Result/Metric signal.

    A bullet counts as having a result if it contains numeric evidence,
    a conservative scale phrase, or an approved metric placeholder.
    """

    if NUMERIC_EVIDENCE_PATTERN.search(bullet):
        return True
    if METRIC_PLACEHOLDER_PATTERN.search(bullet):
        return True
    return bool(SCALE_PHRASE_PATTERN.search(bullet))


def _entry_label(entry: dict[str, Any], index: int) -> str:
    """Human-readable identifier for an experience entry in warnings."""

    for key in ("id", "title", "company_line"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return f"entry #{index}"


def _bullets_missing_result(config: dict[str, Any]) -> list[str]:
    """Locate experience bullets that lack any Result/Metric signal.

    Returns a list of "<entry-label>[<bullet-index>]" labels, one per
    offending bullet. Entries with `suppress_result_check: true` are
    skipped entirely so authors on confidential work are not nagged.
    """

    missing: list[str] = []
    for entry_index, entry in enumerate(config.get("experience", [])):
        if not isinstance(entry, dict):
            continue
        if entry.get("suppress_result_check") is True:
            continue
        role_bullets = entry.get("bullets", [])
        if not isinstance(role_bullets, list):
            continue
        label = _entry_label(entry, entry_index)
        for bullet_index, bullet in enumerate(role_bullets):
            text = str(bullet).strip()
            if not text:
                continue
            if not _bullet_has_result_signal(text):
                missing.append(f"{label}[{bullet_index}]")
    return missing


def _ordered(text: str, labels: list[str]) -> bool:
    positions = []
    lower = text.lower()
    for label in labels:
        position = lower.find(label.lower())
        if position < 0:
            return False
        positions.append(position)
    return positions == sorted(positions)


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value).lower()


# Sentinel for open-ended "present" end dates. Chosen far in the future so the
# overlap comparison sorts correctly against any real month.
_PRESENT_SENTINEL = (9999, 12)


def _parse_experience_month(value: Any) -> tuple[int, int] | None:
    """Parse a structured start/end field into a (year, month) tuple.

    Accepts common ISO-like forms (``YYYY-MM``, ``YYYY-MM-DD``, ``YYYY``),
    plus the special string ``present`` (case-insensitive) for open-ended
    end dates. Returns None when the value cannot be parsed, signalling the
    overlap gate should skip the pair rather than false-positive.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.lower() in {"present", "current", "now"}:
        return _PRESENT_SENTINEL
    match = re.match(r"^(\d{4})(?:-(\d{1,2}))?(?:-\d{1,2})?$", text)
    if not match:
        return None
    year = int(match.group(1))
    month = int(match.group(2)) if match.group(2) else 1
    if not 1 <= month <= 12:
        return None
    return (year, month)


def _experience_date_pair(entry: dict[str, Any]) -> tuple[tuple[int, int], tuple[int, int]] | None:
    """Return (start, end) tuples for an experience entry, or None if absent."""
    start = _parse_experience_month(entry.get("start"))
    end = _parse_experience_month(entry.get("end"))
    if start is None or end is None:
        return None
    return start, end


def _ranges_overlap(
    a: tuple[tuple[int, int], tuple[int, int]],
    b: tuple[tuple[int, int], tuple[int, int]],
) -> bool:
    """Half-open interval overlap: touching endpoints do not overlap."""
    a_start, a_end = a
    b_start, b_end = b
    return a_start < b_end and b_start < a_end


def _format_range(dates: tuple[tuple[int, int], tuple[int, int]]) -> str:
    start, end = dates
    end_label = "present" if end == _PRESENT_SENTINEL else f"{end[0]:04d}-{end[1]:02d}"
    return f"{start[0]:04d}-{start[1]:02d}..{end_label}"


def _same_company_date_overlap(config: dict[str, Any]) -> GateResult:
    """Flag same-company experience entries whose date ranges overlap.

    Requires structured ``start``/``end`` fields on both entries of a pair;
    when either is absent the pair is silently skipped so profiles that have
    not yet migrated to structured dates are not penalised.
    """
    gate = "same_company_date_overlap"
    entries: list[tuple[int, dict[str, Any]]] = []
    for index, entry in enumerate(config.get("experience", [])):
        if isinstance(entry, dict):
            entries.append((index, entry))

    overlaps: list[str] = []
    skipped_pairs = 0
    for i in range(len(entries)):
        index_a, entry_a = entries[i]
        company_a = str(entry_a.get("company", "")).strip().lower()
        if not company_a:
            continue
        dates_a = _experience_date_pair(entry_a)
        for j in range(i + 1, len(entries)):
            index_b, entry_b = entries[j]
            company_b = str(entry_b.get("company", "")).strip().lower()
            if company_a != company_b:
                continue
            dates_b = _experience_date_pair(entry_b)
            if dates_a is None or dates_b is None:
                skipped_pairs += 1
                continue
            if _ranges_overlap(dates_a, dates_b):
                label_a = _entry_label(entry_a, index_a)
                label_b = _entry_label(entry_b, index_b)
                overlaps.append(
                    f"{label_a} ({_format_range(dates_a)}) and "
                    f"{label_b} ({_format_range(dates_b)})"
                )

    if overlaps:
        return GateResult(
            WARN,
            gate,
            f"Same-company date overlap detected: {'; '.join(overlaps)}.",
        )
    if skipped_pairs:
        return GateResult(
            OK,
            gate,
            f"structured dates unavailable for {skipped_pairs} pair(s) — skipped.",
        )
    return GateResult(OK, gate, "No same-company date overlaps detected.")


def run_quality_gates(
    profile: dict[str, Any],
    config: dict[str, Any],
    cv_path: str | Path,
    cover_letter_path: str | Path,
) -> QualityReport:
    """Run deterministic checks on generated application PDFs."""

    results: list[GateResult] = []
    cv, cv_error = _read_pdf(cv_path)
    cover_letter, cl_error = _read_pdf(cover_letter_path)

    if cv_error:
        results.append(GateResult(FAIL, "cv_pdf_readable", cv_error))
    else:
        assert cv is not None
        results.append(GateResult(OK, "cv_pdf_readable", f"{cv.path.name} is readable."))

    if cl_error:
        results.append(GateResult(FAIL, "cover_letter_pdf_readable", cl_error))
    else:
        assert cover_letter is not None
        results.append(
            GateResult(OK, "cover_letter_pdf_readable", f"{cover_letter.path.name} is readable.")
        )

    if cv is None or cover_letter is None:
        return QualityReport(tuple(results))

    cv_text = cv.text
    cl_text = cover_letter.text
    combined_text = f"{cv_text}\n{cl_text}"

    if len(cv_text.strip()) < 500:
        results.append(GateResult(FAIL, "cv_text_extractable", "CV text extraction is too sparse."))
    else:
        results.append(GateResult(OK, "cv_text_extractable", "CV text is extractable."))

    if len(cl_text.strip()) < 250:
        results.append(
            GateResult(FAIL, "cover_letter_text_extractable", "Cover letter text is too sparse.")
        )
    else:
        results.append(
            GateResult(OK, "cover_letter_text_extractable", "Cover letter text is extractable.")
        )

    placeholders = _contains_placeholder(combined_text)
    if placeholders:
        results.append(
            GateResult(
                FAIL,
                "no_placeholder_text",
                f"Generated PDFs contain placeholder-like text: {', '.join(placeholders[:4])}.",
            )
        )
    else:
        results.append(GateResult(OK, "no_placeholder_text", "No placeholder text detected."))

    required_sections = [
        "Professional Summary",
        "Core Skills",
        "Professional Experience",
        "Education",
    ]
    missing_sections = [
        section for section in required_sections if section.lower() not in cv_text.lower()
    ]
    if missing_sections:
        results.append(
            GateResult(
                FAIL,
                "cv_required_sections",
                f"CV is missing required section(s): {', '.join(missing_sections)}.",
            )
        )
    else:
        results.append(GateResult(OK, "cv_required_sections", "Required CV sections are present."))

    canonical_order = [
        "Professional Summary",
        "Core Skills",
        "Professional Experience",
        "Selected Impact",
        "Education",
    ]
    if _ordered(cv_text, canonical_order):
        results.append(GateResult(OK, "cv_section_order", "CV sections are in expected order."))
    else:
        results.append(
            GateResult(WARN, "cv_section_order", "CV section order differs from the expected flow.")
        )

    name = _full_name(profile)
    email = str(profile.get("email", "")).strip()
    compact_cv_text = _compact(cv_text)
    missing_contact = [
        value for value in [name, email] if value and _compact(value) not in compact_cv_text
    ]
    if missing_contact:
        results.append(
            GateResult(
                FAIL,
                "cv_contact_line",
                f"CV text is missing contact value(s): {', '.join(missing_contact)}.",
            )
        )
    else:
        results.append(GateResult(OK, "cv_contact_line", "Name and email are present in CV text."))

    expected_links = []
    if email:
        expected_links.append(f"mailto:{email}")
    links = profile.get("links", {})
    for key in ["linkedin", "github"]:
        url = links.get(key)
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            expected_links.append(url)
    website_url = links.get("blog") or links.get("website")
    if isinstance(website_url, str) and website_url.startswith(("http://", "https://")):
        expected_links.append(website_url)

    all_links = set(cv.links + cover_letter.links)
    missing_links = [link for link in expected_links if link not in all_links]
    if missing_links:
        results.append(
            GateResult(
                WARN,
                "pdf_clickable_links",
                f"Some expected links were not exposed as PDF annotations: {len(missing_links)}.",
            )
        )
    else:
        results.append(GateResult(OK, "pdf_clickable_links", "Expected PDF links are clickable."))

    if cv.image_count or cover_letter.image_count:
        results.append(
            GateResult(
                FAIL,
                "ats_no_images",
                f"Generated PDFs contain {cv.image_count + cover_letter.image_count} image XObject(s).",
            )
        )
    else:
        results.append(GateResult(OK, "ats_no_images", "No embedded images detected."))

    company = str(config.get("company", "")).strip()
    title = str(config.get("title", "")).strip()
    cl_required = [value for value in [company, title] if value]
    missing_cl_context = [value for value in cl_required if value.lower() not in cl_text.lower()]
    if missing_cl_context:
        results.append(
            GateResult(
                FAIL,
                "cover_letter_role_context",
                f"Cover letter is missing role context: {', '.join(missing_cl_context)}.",
            )
        )
    else:
        results.append(
            GateResult(OK, "cover_letter_role_context", "Cover letter includes company and title.")
        )

    if cv.pages > 2:
        results.append(GateResult(WARN, "cv_page_count", f"CV is {cv.pages} pages; target is 1-2."))
    else:
        results.append(GateResult(OK, "cv_page_count", f"CV is {cv.pages} page(s)."))

    if cover_letter.pages > 1:
        results.append(
            GateResult(
                WARN,
                "cover_letter_page_count",
                f"Cover letter is {cover_letter.pages} pages; target is 1.",
            )
        )
    else:
        results.append(GateResult(OK, "cover_letter_page_count", "Cover letter fits on one page."))

    results.append(_same_company_date_overlap(config))

    bullets = _experience_bullets(config)
    normalised_bullets = _normalise_lines(bullets)
    duplicate_count = len(normalised_bullets) - len(set(normalised_bullets))
    if duplicate_count:
        results.append(
            GateResult(WARN, "bullet_repetition", f"{duplicate_count} repeated bullet(s) detected.")
        )
    else:
        results.append(GateResult(OK, "bullet_repetition", "No repeated bullets detected."))

    metric_bullets = [bullet for bullet in bullets if NUMERIC_EVIDENCE_PATTERN.search(bullet)]
    if bullets and len(metric_bullets) < max(1, len(bullets) // 3):
        results.append(
            GateResult(
                WARN,
                "impact_evidence_density",
                "Few experience bullets include numeric or scale evidence; do not invent metrics.",
            )
        )
    else:
        results.append(
            GateResult(OK, "impact_evidence_density", "Impact evidence density is acceptable.")
        )

    additional_experience = config.get("additional_experience", []) or []
    additional_entries = [str(line).strip() for line in additional_experience if str(line).strip()]
    if additional_entries:
        condensed_marker = "earlier experience"
        lower_cv_text = cv_text.lower()
        if condensed_marker not in lower_cv_text:
            results.append(
                GateResult(
                    WARN,
                    "additional_experience_condensed",
                    "additional_experience is present but not rendered as the condensed "
                    "'Earlier experience:' one-line section.",
                )
            )
        else:
            results.append(
                GateResult(
                    OK,
                    "additional_experience_condensed",
                    "additional_experience renders as a condensed one-line section.",
                )
            )

    missing_result = _bullets_missing_result(config)
    if missing_result:
        preview = ", ".join(missing_result[:5])
        suffix = f" (+{len(missing_result) - 5} more)" if len(missing_result) > 5 else ""
        results.append(
            GateResult(
                WARN,
                "per_bullet_result_signal",
                f"Bullets missing Result/Metric signal: {preview}{suffix}.",
            )
        )
    else:
        results.append(
            GateResult(
                OK,
                "per_bullet_result_signal",
                "Every experience bullet carries a Result/Metric signal.",
            )
        )

    weak_hits = [phrase for phrase in WEAK_PHRASES if phrase in combined_text.lower()]
    if weak_hits:
        results.append(
            GateResult(
                WARN,
                "generic_language",
                f"Generic wording detected: {', '.join(sorted(set(weak_hits)))}.",
            )
        )
    else:
        results.append(
            GateResult(OK, "generic_language", "No configured generic phrases detected.")
        )

    return QualityReport(tuple(results))


def format_quality_report(report: QualityReport) -> str:
    """Format a compact CLI report."""

    lines = ["", "Quality gates:"]
    for result in report.results:
        lines.append(f"  {result.status:<4}  {result.name:<28} {result.message}")
    return "\n".join(lines)
