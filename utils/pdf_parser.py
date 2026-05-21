# utils/pdf_parser.py

import io
import html
import pdfplumber

from fastapi import HTTPException

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle,
)
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
)
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors


# =========================================================
# PDF TEXT EXTRACTION
# =========================================================

def extract_text_from_pdf(file_bytes: bytes) -> str:

    raw_text = ""

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:

        for page in pdf.pages:

            text = page.extract_text()

            if text:
                raw_text += text + "\n"

    if not raw_text.strip():

        raise HTTPException(
            status_code=400,
            detail="Unable to read PDF."
        )

    return raw_text.strip()


# =========================================================
# SAFE TEXT
# =========================================================

def safe_text(value) -> str:

    if value is None:
        return ""

    if isinstance(value, str):
        return html.escape(value.strip())

    if isinstance(value, (int, float, bool)):
        return html.escape(str(value))

    if isinstance(value, list):

        cleaned = []

        for item in value:

            rendered = safe_text(item)

            if rendered:
                cleaned.append(rendered)

        return ", ".join(cleaned)

    if isinstance(value, dict):

        cleaned = []

        for _, v in value.items():

            rendered = safe_text(v)

            if rendered:
                cleaned.append(rendered)

        return " | ".join(cleaned)

    return html.escape(str(value))


# =========================================================
# CONTENT DENSITY
# =========================================================

MAX_SINGLE_PAGE_SCORE = 420


def calculate_content_density(resume_data: dict):

    total_chars = len(str(resume_data))

    sections = resume_data.get(
        "sections",
        [],
    )

    total_items = 0

    total_bullets = 0

    for section in sections:

        content = section.get(
            "content",
            [],
        )

        total_items += len(content)

        for item in content:

            if isinstance(item, dict):

                bullets = item.get(
                    "bullets",
                    [],
                )

                if isinstance(bullets, list):
                    total_bullets += len(
                        bullets
                    )

    score = (
        total_chars / 120 +
        total_items * 4 +
        total_bullets * 5
    )

    return score


# =========================================================
# DYNAMIC STYLE ENGINE
# =========================================================

def get_dynamic_styles(score: float):

    styles = getSampleStyleSheet()

    # =====================================================
    # LIGHT CONTENT
    # =====================================================

    if score < 180:

        title_size = 20
        body_size = 10
        line_height = 13

        section_spacing = 12
        item_spacing = 8

    # =====================================================
    # MEDIUM CONTENT
    # =====================================================

    elif score < MAX_SINGLE_PAGE_SCORE:

        title_size = 18
        body_size = 9
        line_height = 11

        section_spacing = 8
        item_spacing = 5

    # =====================================================
    # EXTREME COMPRESSION
    # =====================================================

    else:

        title_size = 14
        body_size = 7.4
        line_height = 8.2

        section_spacing = 3
        item_spacing = 1

    return {
        "title": ParagraphStyle(
            "Title",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=title_size,
            leading=title_size + 2,
            alignment=TA_CENTER,
            textColor=colors.black,
            spaceAfter=4,
        ),

        "heading": ParagraphStyle(
            "Heading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=body_size + 1,
            leading=line_height,
            textColor=colors.black,
            spaceBefore=section_spacing,
            spaceAfter=3,
        ),

        "body": ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=body_size,
            leading=line_height,
            textColor=colors.black,
            spaceAfter=1,
        ),

        "bullet": ParagraphStyle(
            "Bullet",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=body_size,
            leading=line_height,
            leftIndent=10,
            bulletIndent=0,
            spaceAfter=0,
        ),

        "small_gap": item_spacing,
        "section_gap": section_spacing,
    }


# =========================================================
# HELPERS
# =========================================================

def add_paragraph(story, text, style):

    cleaned = safe_text(text)

    if cleaned.strip():

        story.append(
            Paragraph(cleaned, style)
        )


# =========================================================
# PDF GENERATOR
# =========================================================

def generate_pdf_bytes(resume_data: dict) -> bytes:

    buffer = io.BytesIO()

    density_score = calculate_content_density(
        resume_data
    )

    dynamic = get_dynamic_styles(
        density_score
    )

    title_style = dynamic["title"]
    heading_style = dynamic["heading"]
    body_style = dynamic["body"]
    bullet_style = dynamic["bullet"]

    small_gap = dynamic["small_gap"]
    section_gap = dynamic["section_gap"]

    # =====================================================
    # DYNAMIC MARGINS
    # =====================================================

    if density_score > 300:

        margin = 18

    else:

        margin = 28

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=margin,
        leftMargin=margin,
        topMargin=18,
        bottomMargin=18,
    )

    story = []

    basics = resume_data.get(
        "basics",
        {},
    )

    # =====================================================
    # NAME
    # =====================================================

    full_name = basics.get(
        "full_name",
        "",
    )

    if full_name:

        story.append(
            Paragraph(
                safe_text(full_name),
                title_style,
            )
        )

    # =====================================================
    # HEADLINE
    # =====================================================

    headline = basics.get(
        "headline",
        "",
    )

    if headline:

        add_paragraph(
            story,
            headline,
            body_style,
        )

    # =====================================================
    # CONTACT
    # =====================================================

    contact_parts = []

    emails = basics.get(
        "emails",
        [],
    )

    phones = basics.get(
        "phones",
        [],
    )

    location = basics.get(
        "location",
        "",
    )

    links = basics.get(
        "links",
        [],
    )

    if emails:
        contact_parts.extend(emails)

    if phones:
        contact_parts.extend(phones)

    if location:
        contact_parts.append(location)

    # =====================================================
    # FIXED LINK PICKUP
    # =====================================================

    if isinstance(links, list):

        for link in links:

            if isinstance(link, dict):

                label = link.get(
                    "label",
                    "",
                )

                url = link.get(
                    "url",
                    "",
                )

                if label and url:

                    contact_parts.append(
                        f"{label}: {url}"
                    )

                elif url:

                    contact_parts.append(url)

    if contact_parts:

        story.append(
            Paragraph(
                " • ".join(contact_parts),
                body_style,
            )
        )

    story.append(
        Spacer(1, section_gap)
    )

    # =====================================================
    # SECTIONS
    # =====================================================

    sections = resume_data.get(
        "sections",
        [],
    )

    for section in sections:

        title = safe_text(
            section.get("title")
        )

        if not title:
            continue

        story.append(
            Paragraph(
                title.upper(),
                heading_style,
            )
        )

        content = section.get(
            "content",
            [],
        )

        if not isinstance(content, list):
            continue

        # =================================================
        # PURE TAG SECTIONS
        # =================================================

        if all(
            isinstance(x, str)
            for x in content
        ):

            skills = []

            for skill in content:

                cleaned = safe_text(skill)

                if cleaned:
                    skills.append(cleaned)

            if skills:

                story.append(
                    Paragraph(
                        " • ".join(skills),
                        body_style,
                    )
                )

            story.append(
                Spacer(1, small_gap)
            )

            continue

        # =================================================
        # OBJECT CONTENT
        # =================================================

        for item in content:

            if not isinstance(item, dict):
                continue

            # =============================================
            # SUMMARY LINE
            # =============================================

            summary_parts = []

            priority_keys = [
                "title",
                "name",
                "role",
                "company",
                "institution",
                "organization",
                "subtitle",
            ]

            for key in priority_keys:

                value = item.get(key)

                if value:

                    summary_parts.append(
                        safe_text(value)
                    )

            summary = " | ".join(
                summary_parts
            )

            if summary:

                story.append(
                    Paragraph(
                        f"<b>{summary}</b>",
                        body_style,
                    )
                )

            # =============================================
            # META LINE
            # =============================================

            meta_parts = []

            duration = item.get(
                "duration"
            )

            location = item.get(
                "location"
            )

            if duration:
                meta_parts.append(
                    safe_text(duration)
                )

            if location:
                meta_parts.append(
                    safe_text(location)
                )

            if meta_parts:

                story.append(
                    Paragraph(
                        " • ".join(meta_parts),
                        body_style,
                    )
                )

            # =============================================
            # BULLETS
            # =============================================

            bullets = item.get(
                "bullets",
                [],
            )

            if isinstance(bullets, list):

                for bullet in bullets:

                    cleaned = safe_text(
                        bullet
                    )

                    if cleaned:

                        story.append(
                            Paragraph(
                                f"• {cleaned}",
                                bullet_style,
                            )
                        )

            # =============================================
            # TECHNOLOGIES
            # =============================================

            technologies = item.get(
                "technologies",
                [],
            )

            if technologies:

                rendered = safe_text(
                    technologies
                )

                if rendered:

                    story.append(
                        Paragraph(
                            f"<b>Technologies:</b> {rendered}",
                            body_style,
                        )
                    )

            # =============================================
            # EXTRA FIELDS
            # =============================================

            ignored = {
                "title",
                "name",
                "role",
                "company",
                "institution",
                "organization",
                "subtitle",
                "duration",
                "location",
                "bullets",
                "technologies",
            }

            for key, value in item.items():

                if key in ignored:
                    continue

                cleaned = safe_text(
                    value
                )

                if cleaned:

                    story.append(
                        Paragraph(
                            cleaned,
                            body_style,
                        )
                    )

            story.append(
                Spacer(1, small_gap)
            )

        story.append(
            Spacer(1, section_gap)
        )

    # =====================================================
    # BUILD
    # =====================================================

    doc.build(story)

    pdf_bytes = buffer.getvalue()

    buffer.close()

    return pdf_bytes