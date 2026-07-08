"""cv_builder.py — ATS-safe CV PDF builder.

Reads personal data from profile.json; role-specific content from the role config dict.

Usage:
    from cv_builder import build_cv
    build_cv(profile, config, "/path/to/output.pdf")
"""

import sys

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer

DARK = colors.HexColor("#1a1a2e")
GREY = colors.HexColor("#555566")
LGREY = colors.HexColor("#888899")
ACCENT = colors.HexColor("#2563eb")

# Per-entry char cap for the condensed "Earlier experience:" line. Applied only
# when an entry has no ":" to split on, so paragraph-length entries without the
# expected "Role — Company (Context): body" shape still degrade gracefully.
ADDITIONAL_EXPERIENCE_CHAR_CAP = 90


def _condense_additional_experience_entry(entry: str) -> str:
    """Reduce a single additional_experience entry to a condensed label.

    Rule: keep only the pre-colon portion when a ":" is present; otherwise
    truncate at ADDITIONAL_EXPERIENCE_CHAR_CAP with an ellipsis. Trailing
    ":"/"." and whitespace are stripped either way so joined output stays tidy.
    """
    text = entry.strip()
    colon_index = text.find(":")
    if colon_index != -1:
        text = text[:colon_index]
    text = text.rstrip().rstrip(":.").rstrip()
    if colon_index == -1 and len(text) > ADDITIONAL_EXPERIENCE_CHAR_CAP:
        text = f"{text[:ADDITIONAL_EXPERIENCE_CHAR_CAP]}…"
    return text


# Skills tailoring caps. Chosen to fit ~½ page for a senior profile and to
# never invent items outside profile.json. Kept as module-level so tests can
# assert against the same source of truth as the renderer.
SKILLS_MAX_CATEGORIES = 6
SKILLS_MAX_ITEMS_PER_CATEGORY = 6
SKILLS_PADDING_FLOOR = 4
SKILLS_MAX_TOTAL_ITEMS = 40
SKILLS_ITEM_SEPARATOR = "·"


def _get_name(profile: dict) -> str:
    """Extract full name from profile, handling both string and dict formats."""
    name = profile["name"]
    if isinstance(name, dict):
        return f"{name.get('first', '')} {name.get('last', '')}".strip()
    return str(name)


def _get_phone(profile: dict) -> str:
    """Extract a display phone number from supported profile shapes."""

    phone = profile.get("phone", "")
    if isinstance(phone, dict):
        return str(phone.get("formatted") or phone.get("number") or "").strip()
    return str(phone).strip()


CV_DISPLAY_FLAGS = ("show_location", "show_phone")


def resolve_cv_display(profile: dict) -> dict[str, bool]:
    """Return strict-boolean cv_display flags shared by both PDF builders.

    Profiles without a cv_display block, with a non-dict value, or with a
    non-bool flag value render unchanged (all flags True). Non-bool flag
    values also emit a stderr warning so a JSON typo like
    ``"show_phone": "false"`` does not silently leak the field.
    """
    raw = profile.get("cv_display")
    if not isinstance(raw, dict):
        return {flag: True for flag in CV_DISPLAY_FLAGS}
    resolved: dict[str, bool] = {}
    for flag in CV_DISPLAY_FLAGS:
        value = raw.get(flag, True)
        if isinstance(value, bool):
            resolved[flag] = value
        else:
            print(
                f"WARNING: profile.cv_display.{flag} must be a JSON boolean "
                f"(true/false), not {type(value).__name__} {value!r}; treating as true.",
                file=sys.stderr,
            )
            resolved[flag] = True
    return resolved


def _collapse_skill_groups(skills: list[dict]) -> list[dict]:
    """Merge skills entries that share a ``group`` field into one entry per group.

    Entries with a falsy or missing ``group`` are returned as-is. When two or
    more entries share the same non-empty ``group`` value, they are merged into
    a single entry: ``label`` becomes the group name and ``items`` is the
    order-preserving, deduplicated concatenation of their ``items`` strings
    (split on ``·`` and re-joined with the same separator).

    Order of first appearance is preserved for both grouped and ungrouped
    entries: a group occupies the slot of its first member.
    """
    separator = "·"
    grouped_slots: dict[str, int] = {}
    grouped_items: dict[str, list[str]] = {}
    grouped_seen: dict[str, set[str]] = {}
    # First skill entry seen for each group. Used to restore the singleton
    # verbatim when a group ends up with exactly one member — merging a
    # singleton would drop its original label and lose information.
    grouped_singletons: dict[str, dict] = {}
    grouped_counts: dict[str, int] = {}
    output: list[dict | None] = []

    for skill in skills:
        group = skill.get("group") or ""
        if not group:
            output.append(dict(skill))
            continue

        if group not in grouped_slots:
            grouped_slots[group] = len(output)
            grouped_items[group] = []
            grouped_seen[group] = set()
            grouped_singletons[group] = dict(skill)
            grouped_counts[group] = 0
            output.append(None)

        grouped_counts[group] += 1

        items_field = skill.get("items", "")
        for part in items_field.split(separator):
            part = part.strip()
            if part and part not in grouped_seen[group]:
                grouped_seen[group].add(part)
                grouped_items[group].append(part)

    for group, slot in grouped_slots.items():
        if grouped_counts[group] == 1:
            output[slot] = grouped_singletons[group]
        else:
            output[slot] = {
                "label": group,
                "items": f" {separator} ".join(grouped_items[group]),
            }

    return [entry for entry in output if entry is not None]


def _split_items(items_field) -> list[str]:
    """Split a skills ``items`` string on ``·`` (the profile schema separator).

    Whitespace around each part is stripped. Empty parts are discarded.
    A non-string value (defensive: profile authors sometimes pass a list
    literal in tests) is returned as-is after stringifying each element.
    """
    if isinstance(items_field, list):
        return [str(part).strip() for part in items_field if str(part).strip()]
    if not isinstance(items_field, str):
        return []
    return [part.strip() for part in items_field.split(SKILLS_ITEM_SEPARATOR) if part.strip()]


def _tailor_skills_to_jd(skills: list[dict], jd_skills) -> list[dict]:
    """Return a JD-tailored skills list bounded by module-level caps.

    See issue-driven acceptance criteria in the README/CHANGELOG. This function
    is pure: given the same inputs it always returns the same output, no I/O,
    no randomness. Casing of rendered items always follows profile.json —
    JD casing is used only for the case-insensitive comparison key.
    """
    # Normalise the JD list once. `None`, `[]`, or non-list values disable
    # intersection/padding and fall through to a pure cap-only pass so the
    # renderer still shrinks a 13-category profile to the global caps.
    jd_lookup: set[str] = set()
    if isinstance(jd_skills, list):
        for entry in jd_skills:
            if isinstance(entry, str) and entry.strip():
                jd_lookup.add(entry.strip().casefold())

    tailored: list[dict] = []
    padded_only_flags: list[bool] = []

    for skill in skills:
        original_items = _split_items(skill.get("items", ""))
        if not original_items:
            continue

        if jd_lookup:
            matched = [item for item in original_items if item.casefold() in jd_lookup]
            if not matched:
                continue

            # Pad from the same category only, preserving profile order and
            # skipping items already in `matched` (dedupe against the JD hit
            # list, not against the raw category — see property test).
            if len(matched) < SKILLS_PADDING_FLOOR:
                matched_lookup = {item.casefold() for item in matched}
                for item in original_items:
                    if len(matched) >= SKILLS_PADDING_FLOOR:
                        break
                    if item.casefold() in matched_lookup:
                        continue
                    matched.append(item)
                    matched_lookup.add(item.casefold())

            rendered_items = matched[:SKILLS_MAX_ITEMS_PER_CATEGORY]
            jd_hit_count = sum(1 for item in rendered_items if item.casefold() in jd_lookup)
        else:
            rendered_items = original_items[:SKILLS_MAX_ITEMS_PER_CATEGORY]
            # With no JD list every surviving category is treated as
            # "profile-declared", so the drop-preference below applies to none.
            jd_hit_count = len(rendered_items)

        tailored.append(
            {
                "label": skill.get("label", ""),
                "items": f" {SKILLS_ITEM_SEPARATOR} ".join(rendered_items),
            }
        )
        padded_only_flags.append(jd_hit_count == 0)

    # Global category cap. Padded-only categories (0 JD hits after intersection)
    # go first; ties resolved by later profile-declared position so the drop
    # order stays deterministic across runs regardless of dict/hash iteration.
    if len(tailored) > SKILLS_MAX_CATEGORIES:
        drop_order = sorted(
            range(len(tailored)),
            key=lambda i: (0 if padded_only_flags[i] else 1, -i),
        )
        to_drop = set(drop_order[: len(tailored) - SKILLS_MAX_CATEGORIES])
        tailored = [entry for i, entry in enumerate(tailored) if i not in to_drop]

    # Global item cap. Trim one item from the tail category at a time so a
    # cluster of small categories is preserved and only the last (least
    # profile-priority) block shrinks.
    def _count_total(entries: list[dict]) -> int:
        return sum(len(_split_items(entry["items"])) for entry in entries)

    while _count_total(tailored) > SKILLS_MAX_TOTAL_ITEMS and tailored:
        tail = tailored[-1]
        tail_items = _split_items(tail["items"])
        if len(tail_items) <= 1:
            tailored.pop()
            continue
        tail_items.pop()
        tail["items"] = f" {SKILLS_ITEM_SEPARATOR} ".join(tail_items)

    return tailored


def is_current_role(role: dict) -> bool:
    """Return True when the experience entry's ``end`` marks it as ongoing.

    Metadata helper for consumers that need to know whether a role is
    current (e.g. tense selection, recency ordering). Rendering is
    unchanged: ``company_line`` remains the sole display source.
    """
    return role.get("end") == "present"


def _s(name, **kw):
    base = dict(
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=DARK,
        spaceAfter=0,
        spaceBefore=0,
    )
    base.update(kw)
    return ParagraphStyle(name, **base)


def build_cv(profile: dict, config: dict, output_path: str) -> None:
    """
    Build a tailored CV PDF.

    profile keys (from profile.json):
        name            str   Full name
        email           str
        location        str   e.g. "Lagos, Nigeria"
        openness        str   Banner line shown under headline (per-role override
                              wins; ATS-only data lives in `relocation`).
        links           dict  {linkedin, github, website, blog}
        education       list[str]   Degree lines
        certifications  list[str]   Certification lines (optional)

    config keys (from roles/<id>.json):
        company                  str
        title                    str
        headline                 str   Subtitle line under name
        openness                 str   Availability line (optional, overrides profile.openness)
        summary                  str   HTML-safe summary paragraph
        skills                   list[{label, items}]
        experience               list[{title, company_line, client_line?, bullets: list[str],
                                       type?: employment|open_source|consulting|contract,
                                       tech_stack?: str}]
        additional_experience    list[str]  Older/minor roles rendered as one
                                            condensed line prefixed
                                            "Earlier experience:" (optional)
        projects                 list[{title, tech_line, bullets: list[str]}]  (optional)
    """
    full_name = _get_name(profile)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title=f"{full_name} — {config.get('company', 'CV')}",
        author=full_name,
    )

    NAME = _s(
        "name", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=DARK, spaceAfter=1
    )
    ROLETITLE = _s("role", fontSize=11, textColor=GREY, spaceAfter=1)
    OPENNESS = _s("open", fontSize=9, textColor=LGREY, fontName="Helvetica-Oblique", spaceAfter=2)
    CONTACT = _s("con", fontSize=8.5, textColor=LGREY, spaceAfter=0)
    SEC_HEAD = _s(
        "sec",
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=DARK,
        spaceBefore=9,
        spaceAfter=2,
        textTransform="uppercase",
        letterSpacing=0.8,
    )
    JOB_TITLE = _s(
        "jt", fontName="Helvetica-Bold", fontSize=9.5, textColor=DARK, spaceAfter=0, spaceBefore=5
    )
    COMPANY = _s("co", fontName="Helvetica-Oblique", fontSize=9, textColor=GREY, spaceAfter=3)
    CLIENT = _s("cl", fontName="Helvetica-Oblique", fontSize=8.5, textColor=LGREY, spaceAfter=3)
    BULLET = _s("bul", leftIndent=11, firstLineIndent=-9, spaceAfter=1.8)
    SUMMARY = _s("sum", fontSize=9.5, leading=14, spaceAfter=0)
    EDU = _s("edu", spaceAfter=2)
    SK = _s("sk", spaceAfter=3, leading=13)

    def rule():
        return HRFlowable(
            width="100%",
            thickness=0.4,
            color=colors.HexColor("#d1d5db"),
            spaceAfter=5,
            spaceBefore=0,
        )

    def section(title):
        return [Paragraph(title, SEC_HEAD), rule()]

    def bul(text):
        return Paragraph(f"<bullet>•</bullet> {text}", BULLET)

    def sp(n=4):
        return Spacer(1, n)

    # ── Build contact line from profile ──────────────────────────────────────
    # cv_display lets users suppress display-only fields (location, phone)
    # from generated PDFs without touching the raw profile values used by
    # ATS forms. See resolve_cv_display for default semantics.
    # profile.relocation is ATS metadata only; the CV banner uses config.openness
    # (per-role) or profile.openness (default) instead.
    links = profile.get("links", {})
    cv_display = resolve_cv_display(profile)
    contact_parts = [
        profile.get("location", "") if cv_display["show_location"] else "",
    ]
    if profile.get("email"):
        contact_parts.append(
            f'<a href="mailto:{profile["email"]}" color="#2563eb">{profile["email"]}</a>'
        )
    phone = _get_phone(profile) if cv_display["show_phone"] else ""
    if phone:
        contact_parts.append(phone)
    if links.get("linkedin"):
        contact_parts.append(f'<a href="{links["linkedin"]}" color="#2563eb">LinkedIn</a>')
    if links.get("github"):
        contact_parts.append(f'<a href="{links["github"]}" color="#2563eb">GitHub</a>')
    if links.get("blog") or links.get("website"):
        url = links.get("blog") or links.get("website")
        label = url.replace("https://", "").replace("http://", "")
        contact_parts.append(f'<a href="{url}" color="#2563eb">{label}</a>')

    contact_line = " &nbsp;·&nbsp; ".join(p for p in contact_parts if p)

    story = []

    # ── Header ───────────────────────────────────────────────────────────────
    # openness defaults to "" — prepare_generation_config fills it from
    # profile.openness, and a per-role roles/<id>.json can override.
    story += [
        Paragraph(full_name, NAME),
        Paragraph(config["headline"], ROLETITLE),
    ]
    openness_text = config.get("openness", "") or ""
    if openness_text:
        story.append(Paragraph(openness_text, OPENNESS))
    story += [
        Paragraph(contact_line, CONTACT),
        sp(10),
    ]

    # ── Professional Summary ─────────────────────────────────────────────────
    story += section("Professional Summary")
    story += [Paragraph(config["summary"], SUMMARY), sp(6)]

    # ── Core Skills ──────────────────────────────────────────────────────────
    # Group collapse runs first so user-declared ``group`` intent still applies,
    # then JD tailoring filters/caps the collapsed representation. Missing
    # jd_skills falls through to a pure cap-only pass (v1.9.0 categories/items
    # over the caps get trimmed; anything within stays as-is).
    collapsed_skills = _collapse_skill_groups(config["skills"])
    tailored_skills = _tailor_skills_to_jd(collapsed_skills, config.get("jd_skills"))
    story += section("Core Skills")
    for skill in tailored_skills:
        story.append(Paragraph(f"<b>{skill['label']}</b>:&nbsp;&nbsp;{skill['items']}", SK))
    story.append(sp(4))

    # ── Professional Experience ───────────────────────────────────────────────
    # entry.type routes an experience item to a CV section: `open_source` →
    # Projects, anything else (including missing) → Work Experience. Order is
    # preserved within each section.
    work_experience = [
        role for role in config["experience"] if role.get("type", "employment") != "open_source"
    ]
    open_source_experience = [
        role for role in config["experience"] if role.get("type") == "open_source"
    ]
    story += section("Professional Experience")
    for role in work_experience:
        header_parts = [Paragraph(role["title"], JOB_TITLE)]
        if role.get("company_line"):
            header_parts.append(Paragraph(role["company_line"], COMPANY))
        if role.get("client_line"):
            header_parts.append(Paragraph(role["client_line"], CLIENT))
        story.append(KeepTogether(header_parts))
        bullets = role.get("bullets", [])
        if isinstance(bullets, dict):
            bullets = bullets.get("default", [])
        for b in bullets:
            story.append(bul(b))
        tech_stack = role.get("tech_stack")
        if tech_stack:
            story.append(Paragraph(f"<b>Tech Stack:</b>&nbsp;{tech_stack}", SUMMARY))
        story.append(sp(4))

    # ── Earlier Experience (optional, condensed one-liner) ────────────────────
    # Rendered as a single condensed paragraph to preserve page budget rather
    # than expanding into full entry blocks. Entries are joined by " · " and
    # prefixed with "Earlier experience:". Omitted entirely when empty/absent.
    additional = config.get("additional_experience", [])
    if additional:
        entries = [
            _condense_additional_experience_entry(str(line))
            for line in additional
            if str(line).strip()
        ]
        entries = [entry for entry in entries if entry]
        if entries:
            joined = " · ".join(entries)
            story.append(Paragraph(f"<b>Earlier experience:</b>&nbsp;{joined}", SUMMARY))
            story.append(sp(4))

    # ── Education ────────────────────────────────────────────────────────────
    story += section("Education")
    for edu in profile.get("education", []):
        # Handle both string and dict formats
        if isinstance(edu, dict):
            parts = [edu.get("degree", ""), edu.get("institution", ""), edu.get("year", "")]
            edu_str = " — ".join(p for p in parts if p)
        else:
            edu_str = str(edu)
        story.append(Paragraph(edu_str, EDU))

    # ── Projects (optional) ───────────────────────────────────────────────────
    # Merges open_source experience entries with any config["projects"]. For
    # experience items, company_line acts as the tech context line.
    projects = config.get("projects") or []
    if projects or open_source_experience:
        story += section("Projects")
        for role in open_source_experience:
            story.append(Paragraph(role["title"], JOB_TITLE))
            tech_line = role.get("company_line") or role.get("client_line") or ""
            if tech_line:
                story.append(Paragraph(tech_line, CLIENT))
            bullets = role.get("bullets", [])
            if isinstance(bullets, dict):
                bullets = bullets.get("default", [])
            for b in bullets:
                story.append(bul(b))
            tech_stack = role.get("tech_stack")
            if tech_stack:
                story.append(Paragraph(f"<b>Tech Stack:</b>&nbsp;{tech_stack}", SUMMARY))
            story.append(sp(4))
        for proj in projects:
            story.append(Paragraph(proj["title"], JOB_TITLE))
            if proj.get("tech_line"):
                story.append(Paragraph(proj["tech_line"], CLIENT))
            for b in proj.get("bullets", []):
                story.append(bul(b))
            story.append(sp(4))

    # ── Awards & Recognition (optional) ──────────────────────────────────────
    # Sources the profile.certifications field (name retained for backward
    # compatibility); the heading reflects the current content mix.
    certs = profile.get("certifications", [])
    if certs:
        story += section("Awards &amp; Recognition")
        for cert in certs:
            story.append(bul(cert))
        story.append(sp(4))

    doc.build(story)
    print(f"  ✓ CV PDF → {output_path}")
