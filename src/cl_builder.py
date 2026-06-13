"""cl_builder.py — Cover letter PDF builder.

Reads personal data from profile.json; role-specific content from the role config dict.

Usage:
    from cl_builder import build_cover_letter
    build_cover_letter(profile, config, "/path/to/output.pdf")
"""

import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

DARK = colors.HexColor("#1a1a2e")
GREY = colors.HexColor("#555566")
LGREY = colors.HexColor("#888899")


def _s(name, **kw):
    base = dict(
        fontName="Helvetica", fontSize=10, leading=15, textColor=DARK, spaceAfter=0, spaceBefore=0
    )
    base.update(kw)
    return ParagraphStyle(name, **base)


def build_cover_letter(profile: dict, config: dict, output_path: str) -> None:
    """
    Build a tailored cover letter PDF.

    profile keys (from profile.json):
        name    str
        email   str
        location str
        links   dict  {linkedin, github, website, blog}

    config must contain a 'cover_letter' sub-dict with keys:
        salutation    str   e.g. "Dear Hiring Team,"
        paragraphs    list[str]   HTML-safe body paragraphs
        closing       str   e.g. "Best regards,"
    """
    cl = config.get("cover_letter", {})
    links = profile.get("links", {})

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title=f"{profile['name']} — Cover Letter — {config.get('company', '')}",
        author=profile["name"],
    )

    NAME = _s(
        "name", fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=DARK, spaceAfter=2
    )
    CONTACT = _s("con", fontSize=8.5, textColor=LGREY, spaceAfter=0)
    DATE = _s("date", fontSize=9.5, textColor=LGREY, spaceAfter=12)
    DEST = _s(
        "dest", fontName="Helvetica-Bold", fontSize=9.5, textColor=DARK, spaceAfter=4, spaceBefore=4
    )
    SALUTE = _s("sal", fontName="Helvetica-Bold", fontSize=10, textColor=DARK, spaceAfter=10)
    BODY = _s("body", fontSize=10, leading=15.5, textColor=DARK, spaceAfter=10)
    CLOSE = _s("cls", fontSize=10, textColor=DARK, spaceAfter=6, spaceBefore=8)
    SIG = _s("sig", fontName="Helvetica-Bold", fontSize=10, textColor=DARK)

    def rule():
        return HRFlowable(
            width="100%",
            thickness=0.4,
            color=colors.HexColor("#d1d5db"),
            spaceAfter=8,
            spaceBefore=2,
        )

    def sp(n=6):
        return Spacer(1, n)

    # ── Build contact line ───────────────────────────────────────────────────
    contact_parts = []
    if profile.get("location"):
        contact_parts.append(profile["location"])
    if profile.get("email"):
        contact_parts.append(
            f'<a href="mailto:{profile["email"]}" color="#2563eb">{profile["email"]}</a>'
        )
    if links.get("linkedin"):
        contact_parts.append(f'<a href="{links["linkedin"]}" color="#2563eb">LinkedIn</a>')
    if links.get("blog") or links.get("website"):
        url = links.get("blog") or links.get("website")
        label = url.replace("https://", "").replace("http://", "")
        contact_parts.append(f'<a href="{url}" color="#2563eb">{label}</a>')

    contact_line = " &nbsp;·&nbsp; ".join(contact_parts)
    date_str = datetime.datetime.now().strftime("%B %Y")

    story = []

    # ── Letterhead ───────────────────────────────────────────────────────────
    story += [
        Paragraph(profile["name"], NAME),
        Paragraph(contact_line, CONTACT),
        rule(),
    ]

    # ── Date + Destination ───────────────────────────────────────────────────
    story += [
        Paragraph(date_str, DATE),
        Paragraph(f"{config.get('company', '')} — {config.get('title', '')}", DEST),
        sp(4),
    ]

    # ── Salutation ───────────────────────────────────────────────────────────
    story.append(Paragraph(cl.get("salutation", "Dear Hiring Team,"), SALUTE))

    # ── Body paragraphs ──────────────────────────────────────────────────────
    for para in cl.get("paragraphs", []):
        story.append(Paragraph(para, BODY))

    # ── Sign-off ─────────────────────────────────────────────────────────────
    story += [
        sp(4),
        Paragraph(cl.get("closing", "Best regards,"), CLOSE),
        Paragraph(profile["name"], SIG),
    ]

    doc.build(story)
    print(f"  ✓ Cover letter → {output_path}")
