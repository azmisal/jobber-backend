import io
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
            detail="Unreadable PDF.",
        )

    return raw_text


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
        "Title",
        parent=styles["Heading1"],
        fontSize=24,
        spaceAfter=10,
    )

    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=12,
        spaceAfter=8,
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        spaceAfter=4,
    )

    bullet_style = ParagraphStyle(
        "Bullet",
        parent=styles["Normal"],
        leftIndent=14,
        fontSize=10,
        leading=14,
        spaceAfter=4,
    )

    story = []

    basics = resume_data.get("basics", {})

    if basics.get("full_name"):
        story.append(
            Paragraph(
                basics["full_name"],
                title_style,
            )
        )

    top_line = []

    if basics.get("headline"):
        top_line.append(basics["headline"])

    top_line.extend(basics.get("emails", []))
    top_line.extend(basics.get("phones", []))

    if basics.get("location"):
        top_line.append(basics["location"])

    for link in basics.get("links", []):

        if isinstance(link, dict):
            url = link.get("url")

            if url:
                top_line.append(url)

    if top_line:
        story.append(
            Paragraph(
                " | ".join(top_line),
                body_style,
            )
        )

    story.append(Spacer(1, 10))

    sections = resume_data.get("sections", [])

    for section in sections:

        title = section.get("title", "")

        if title:
            story.append(
                Paragraph(
                    title,
                    heading_style,
                )
            )

        content = section.get("content", [])

        for item in content:

            # SIMPLE STRING TAGS / SKILLS

            if isinstance(item, str):

                story.append(
                    Paragraph(
                        f"• {item}",
                        bullet_style,
                    )
                )

            # STRUCTURED OBJECTS

            elif isinstance(item, dict):

                title_line = []

                if item.get("title"):
                    title_line.append(item["title"])

                if item.get("subtitle"):
                    title_line.append(item["subtitle"])

                if item.get("duration"):
                    title_line.append(item["duration"])

                if title_line:
                    story.append(
                        Paragraph(
                            f"<b>{' | '.join(title_line)}</b>",
                            body_style,
                        )
                    )

                bullets = item.get("bullets", [])

                if bullets:

                    for bullet in bullets:

                        story.append(
                            Paragraph(
                                f"• {bullet}",
                                bullet_style,
                            )
                        )

                # IMPORTANT:
                # only render description if exists

                description = item.get("description")

                if description:

                    story.append(
                        Paragraph(
                            description,
                            body_style,
                        )
                    )

            story.append(Spacer(1, 4))

    doc.build(story)

    buffer.seek(0)

    return buffer.getvalue()