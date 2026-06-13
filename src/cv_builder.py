"""cv_builder.py — ATS-optimised CV PDF builder.

Reads personal data from profile.json; role-specific content from the role config dict.

Usage:
    from cv_builder import build_cv
    build_cv(profile, config, "/path/to/output.pdf")
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer

DARK = colors.HexColor("#1a1a2e")
GREY = colors.HexColor("#555566")
LGREY = colors.HexColor("#888899")
ACCENT = colors.HexColor("#2563eb")


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
        relocation      str   e.g. "Open to EU / UK / US relocation"
        links           dict  {linkedin, github, website, blog}
        education       list[str]   Degree lines
        certifications  list[str]   Certification lines (optional)

    config keys (from roles/<id>.json):
        company         str
        title           str
        headline        str   Subtitle line under name
        openness        str   Availability line (optional)
        summary         str   HTML-safe summary paragraph
        impact_statements list[{title, body}]
        experience      list[{title, company_line, client_line?, bullets: list[str]}]
        skills          list[{label, items}]
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title=f"{profile['name']} — {config.get('company', 'CV')}",
        author=profile["name"],
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
    IMPACT_H = _s(
        "imph",
        fontName="Helvetica-Bold",
        fontSize=9.5,
        textColor=ACCENT,
        spaceAfter=1,
        spaceBefore=3,
    )
    IMPACT_B = _s("impb", fontSize=9, textColor=GREY, spaceAfter=4, leading=13)
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
    links = profile.get("links", {})
    contact_parts = [
        profile.get("location", ""),
        profile.get("relocation", ""),
    ]
    if profile.get("email"):
        contact_parts.append(
            f'<a href="mailto:{profile["email"]}" color="#2563eb">{profile["email"]}</a>'
        )
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
    story += [
        Paragraph(profile["name"], NAME),
        Paragraph(config["headline"], ROLETITLE),
        Paragraph(
            config.get(
                "openness", "Open to fully remote roles globally and relocation for the right team."
            ),
            OPENNESS,
        ),
        Paragraph(contact_line, CONTACT),
        sp(10),
    ]

    # ── Summary ──────────────────────────────────────────────────────────────
    story += section("Summary")
    story += [Paragraph(config["summary"], SUMMARY), sp(6)]

    # ── Selected Impact ──────────────────────────────────────────────────────
    story += section("Selected Impact")
    for item in config["impact_statements"]:
        story.append(
            KeepTogether(
                [
                    Paragraph(f'<b><font color="#2563eb">{item["title"]}</font></b>', IMPACT_H),
                    Paragraph(item["body"], IMPACT_B),
                ]
            )
        )
    story.append(sp(2))

    # ── Experience ───────────────────────────────────────────────────────────
    story += section("Experience")
    for role in config["experience"]:
        header_parts = [Paragraph(role["title"], JOB_TITLE)]
        if role.get("company_line"):
            header_parts.append(Paragraph(role["company_line"], COMPANY))
        if role.get("client_line"):
            header_parts.append(Paragraph(role["client_line"], CLIENT))
        story.append(KeepTogether(header_parts))
        for b in role["bullets"]:
            story.append(bul(b))
        story.append(sp(4))

    # ── Skills ───────────────────────────────────────────────────────────────
    story += section("Core Skills")
    for skill in config["skills"]:
        story.append(Paragraph(f"<b>{skill['label']}</b>:&nbsp;&nbsp;{skill['items']}", SK))
    story.append(sp(4))

    # ── Certifications (optional) ────────────────────────────────────────────
    certs = profile.get("certifications", [])
    if certs:
        story += section("Certifications &amp; Community")
        for cert in certs:
            story.append(bul(cert))
        story.append(sp(4))

    # ── Education ────────────────────────────────────────────────────────────
    story += section("Education")
    for edu in profile.get("education", []):
        story.append(Paragraph(edu, EDU))

    doc.build(story)
    print(f"  ✓ CV PDF → {output_path}")
