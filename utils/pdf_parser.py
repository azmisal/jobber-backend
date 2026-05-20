# utils/pdf_parser.py

import io
import html
import pdfplumber

from fastapi import HTTPException

from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
)
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle,
)

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

    return raw_text


# =========================================================
# SAFE HELPERS
# =========================================================

def safe_text(value) -> str:

    """
    Safely converts ANY value into renderable string.
    """

    if value is None:
        return ""

    # -----------------------------------
    # STRING
    # -----------------------------------

    if isinstance(value, str):

        return html.escape(value.strip())

    # -----------------------------------
    # NUMBER / BOOL
    # -----------------------------------

    if isinstance(value, (int, float, bool)):

        return html.escape(str(value))

    # -----------------------------------
    # LIST
    # -----------------------------------

    if isinstance(value, list):

        parts = []

        for item in value:

            if isinstance(item, str):

                cleaned = item.strip()

                if cleaned:
                    parts.append(cleaned)

            elif isinstance(item, dict):

                inner = []

                for k, v in item.items():

                    if not v:
                        continue

                    rendered = safe_text(v)

                    if rendered:
                        inner.append(rendered)

                if inner:
                    parts.append(" | ".join(inner))

            else:

                parts.append(str(item))

        return html.escape(", ".join(parts))

    # -----------------------------------
    # DICT
    # -----------------------------------

    if isinstance(value, dict):

        parts = []

        for k, v in value.items():

            if not v:
                continue

            rendered = safe_text(v)

            if rendered:
                parts.append(rendered)

        return html.escape(" | ".join(parts))

    # -----------------------------------
    # FALLBACK
    # -----------------------------------

    return html.escape(str(value))


def add_paragraph(story, text, style):

    cleaned = safe_text(text)

    if cleaned.strip():

        story.append(
            Paragraph(cleaned, style)
        )


# =========================================================
# UNIVERSAL PDF GENERATOR
# =========================================================

def generate_pdf_bytes(resume_data: dict) -> bytes:

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ResumeTitle",
        parent=styles["Heading1"],
        fontSize=22,
        leading=28,
        spaceAfter=14,
    )

    heading_style = ParagraphStyle(
        "ResumeHeading",
        parent=styles["Heading2"],
        fontSize=14,
        leading=18,
        spaceBefore=12,
        spaceAfter=8,
    )

    body_style = ParagraphStyle(
        "ResumeBody",
        parent=styles["Normal"],
        fontSize=10,
        leading=15,
        spaceAfter=6,
    )

    bullet_style = ParagraphStyle(
        "ResumeBullet",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        leftIndent=15,
        spaceAfter=4,
    )

    story = []

    # =====================================================
    # BASICS
    # =====================================================

    basics = resume_data.get("basics", {})

    full_name = basics.get("full_name", "")

    if full_name:

        story.append(
            Paragraph(
                safe_text(full_name),
                title_style
            )
        )

    headline = basics.get("headline")

    if headline:

        add_paragraph(
            story,
            headline,
            body_style
        )

    contact_parts = []

    emails = basics.get("emails", [])
    phones = basics.get("phones", [])
    location = basics.get("location", "")
    links = basics.get("links", [])

    if emails:
        contact_parts.append(", ".join(emails))

    if phones:
        contact_parts.append(", ".join(phones))

    if location:
        contact_parts.append(location)

    if links:

        link_strings = []

        for link in links:

            if isinstance(link, dict):

                label = link.get("label", "")
                url = link.get("url", "")

                if label and url:
                    link_strings.append(f"{label}: {url}")

                elif url:
                    link_strings.append(url)

        if link_strings:
            contact_parts.append(" | ".join(link_strings))

    if contact_parts:

        add_paragraph(
            story,
            " • ".join(contact_parts),
            body_style
        )

    story.append(Spacer(1, 12))

    # =====================================================
    # DYNAMIC SECTIONS
    # =====================================================

    sections = resume_data.get("sections", [])

    for section in sections:

        title = section.get("title", "").strip()

        if not title:
            continue

        story.append(
            Paragraph(
                safe_text(title),
                heading_style
            )
        )

        content = section.get("content", [])

        if not isinstance(content, list):
            continue

        for item in content:

            # ============================================
            # STRING ITEM
            # ============================================

            if isinstance(item, str):

                cleaned = item.strip()

                if cleaned:

                    story.append(
                        Paragraph(
                            f"• {safe_text(cleaned)}",
                            bullet_style
                        )
                    )

                continue

            # ============================================
            # OBJECT ITEM
            # ============================================

            if isinstance(item, dict):

                fields = list(item.items())

                if not fields:
                    continue

                first_line_rendered = False

                # ----------------------------------------
                # Render key summary line
                # ----------------------------------------

                summary_parts = []

                preferred_keys = [
                    "title",
                    "name",
                    "role",
                    "company",
                    "institution",
                    "organization",
                    "subtitle",
                    "duration",
                    "date",
                ]

                used_keys = set()

                for key in preferred_keys:

                    value = item.get(key)

                    if value:

                        summary_parts.append(
                            safe_text(value)
                        )

                        used_keys.add(key)

                if summary_parts:

                    story.append(
                        Paragraph(
                            "<b>" + " | ".join(summary_parts) + "</b>",
                            body_style
                        )
                    )

                    first_line_rendered = True

                # ----------------------------------------
                # Render remaining fields
                # ----------------------------------------

                for key, value in item.items():

                    if key in used_keys:
                        continue

                    if not value:
                        continue

                    # bullets array
                    if isinstance(value, list):

                        if key.lower() == "bullets":

                            for bullet in value:

                                bullet_text = safe_text(bullet)

                                if bullet_text.strip():

                                    story.append(
                                        Paragraph(
                                            f"• {bullet_text}",
                                            bullet_style
                                        )
                                    )

                        else:

                            rendered = safe_text(value)

                            if rendered.strip():

                                story.append(
                                    Paragraph(
                                        rendered,
                                        body_style
                                    )
                                )

                    # string fields
                    else:

                        rendered = safe_text(value)

                        if rendered.strip():

                            story.append(
                                Paragraph(
                                    rendered,
                                    body_style
                                )
                            )

                story.append(
                    Spacer(1, 6)
                )

        story.append(
            Spacer(1, 10)
        )

    # =====================================================
    # BUILD
    # =====================================================

    doc.build(story)

    buffer.seek(0)

    return buffer.getvalue()