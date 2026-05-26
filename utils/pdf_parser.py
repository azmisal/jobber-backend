# =========================================================
# LINK EXTRACTION & ANNOTATION
# =========================================================
import html
import re
from urllib.parse import urlparse

EMAIL_RE = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    re.IGNORECASE,
)
URL_RE = re.compile(
    r"(?:(?:https?://|www\.)[^\s<>()]+|(?<!@)\b(?:linkedin\.com|github\.com)/[^\s<>()]+|(?<!@)\b[a-z0-9][a-z0-9-]*(?:\.[a-z0-9][a-z0-9-]*)+\.(?:app|co|com|dev|in|io|me|net|org)(?:/[^\s<>()]*)?)",
    re.IGNORECASE,
)
PHONE_RE = re.compile(
    r"(?<!\w)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{4}(?!\w)"
)


def normalize_url(url: str) -> str:
    url = str(url or "").strip().rstrip(".,;:")

    if not url:
        return ""

    lowered = url.lower()

    if lowered.startswith(("http://", "https://", "mailto:", "tel:")):
        return url

    if lowered.startswith("www."):
        return f"https://{url}"

    if "/" in url and "." in url.split("/", 1)[0]:
        return f"https://{url}"

    if (
        "." in url
        and "@" not in url
        and not re.search(r"\s", url)
    ):
        return f"https://{url}"

    return url


def clean_link_label(label: str) -> str:
    label = re.sub(r"\s+", " ", str(label or "")).strip()
    return label.strip(" \t\n\r|•-–—:;")


def as_list(value) -> list:
    if isinstance(value, list):
        return value

    if value in (None, ""):
        return []

    return [value]


def escape_href(url: str) -> str:
    return html.escape(normalize_url(url), quote=True)


def make_anchor(label: str, url: str) -> str:
    href = escape_href(url)

    if not href:
        return label

    return f'<a href="{href}">{label}</a>'


def link_key(link: dict) -> tuple:
    return (
        clean_link_label(link.get("label", "")).lower(),
        normalize_url(link.get("url", "")).lower(),
    )


def append_unique_link(links: list, label: str, url: str) -> None:
    label = clean_link_label(label)
    url = normalize_url(url)

    if not url:
        return

    if not label:
        label = classify_link_label(url)

    candidate = {
        "label": label,
        "url": url,
    }

    candidate_url = normalize_url(url).lower()

    for existing in links:
        if not isinstance(existing, dict):
            continue

        existing_url = normalize_url(
            existing.get("url", "")
        ).lower()

        if existing_url != candidate_url:
            continue

        existing_label = clean_link_label(
            existing.get("label", "")
        )

        if label and (
            not existing_label
            or existing_label.lower()
            == existing_url
            or existing_label.lower()
            == classify_link_label(url).lower()
        ):
            existing["label"] = label

        return

    if link_key(candidate) not in {link_key(link) for link in links}:
        links.append(candidate)


def classify_link_label(url: str, fallback: str = "") -> str:
    if fallback:
        return clean_link_label(fallback)

    parsed = urlparse(normalize_url(url))
    host = parsed.netloc.lower()

    if not host and parsed.scheme in {"mailto", "tel"}:
        host = parsed.scheme

    if "linkedin.com" in host:
        return "LinkedIn"

    if "github.com" in host:
        return "GitHub"

    if parsed.scheme == "mailto":
        return "Email"

    if parsed.scheme == "tel":
        return "Phone"

    return "Portfolio" if host else clean_link_label(url)


def annotate_known_link_labels(text: str, known_links: list[dict] | None) -> str:
    if not text or not known_links:
        return text

    parts = re.split(
        r"(<a\b[^>]*>.*?</a>)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    labels = []

    for link in known_links:
        if not isinstance(link, dict):
            continue

        label = clean_link_label(link.get("label", ""))
        url = normalize_url(link.get("url", ""))

        if not label or not url:
            continue

        if EMAIL_RE.fullmatch(label) or URL_RE.fullmatch(label):
            continue

        labels.append(
            (
                html.escape(label),
                url,
            )
        )

    labels.sort(
        key=lambda item: len(item[0]),
        reverse=True,
    )

    for index, part in enumerate(parts):
        if part.lower().startswith("<a "):
            continue

        for label, url in labels:
            pattern = re.compile(
                rf"(?<![\w/]){re.escape(label)}(?![\w/])"
            )
            part = pattern.sub(
                lambda match: make_anchor(match.group(0), url),
                part,
            )

        parts[index] = part

    return "".join(parts)


def annotate_bare_urls(text: str) -> str:
    parts = re.split(
        r"(<a\b[^>]*>.*?</a>)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    def url_repl(match):
        url = match.group(0)
        return make_anchor(url, url)

    for index, part in enumerate(parts):
        if part.lower().startswith("<a "):
            continue

        parts[index] = re.sub(URL_RE, url_repl, part)

    return "".join(parts)


def annotate_links(text: str, known_links: list[dict] | None = None) -> str:
    """
    Finds URLs in the text and wraps them with <a href="...">...</a> for ReportLab.
    If a URL is already embedded as markdown [text](url), preserve the display text and link.
    """
    if not text:
        return ""

    # Convert markdown links [text](url) to <a href="url">text</a>
    def md_repl(match):
        label, url = match.group(1), match.group(2)
        return make_anchor(label, html.unescape(url))
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', md_repl, text)

    text = annotate_bare_urls(text)

    text = annotate_known_link_labels(text, known_links)

    return text
# utils/pdf_parser.py

import io
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

def extract_annotation_uri(annotation: dict) -> str:
    uri = (
        annotation.get("uri")
        or annotation.get("url")
        or annotation.get("URI")
    )

    if uri:
        return str(uri)

    action = annotation.get("A") or annotation.get("action")

    if isinstance(action, dict):
        return str(
            action.get("URI")
            or action.get("uri")
            or ""
        )

    data = annotation.get("data")

    if isinstance(data, dict):
        action = data.get("A")

        if isinstance(action, dict):
            return str(
                action.get("URI")
                or action.get("uri")
                or ""
            )

    return ""


def annotation_bbox(annotation: dict):
    if all(key in annotation for key in ("x0", "top", "x1", "bottom")):
        return (
            annotation["x0"],
            annotation["top"],
            annotation["x1"],
            annotation["bottom"],
        )

    if all(key in annotation for key in ("x0", "y0", "x1", "y1")):
        return (
            annotation["x0"],
            annotation["y0"],
            annotation["x1"],
            annotation["y1"],
        )

    rect = annotation.get("rect") or annotation.get("Rect")

    if isinstance(rect, (list, tuple)) and len(rect) == 4:
        return tuple(rect)

    return None


def extract_annotation_label(page, annotation: dict) -> str:
    label = (
        annotation.get("text")
        or annotation.get("title")
        or annotation.get("contents")
        or annotation.get("Contents")
        or ""
    )

    label = clean_link_label(label)

    if label:
        return label

    bbox = annotation_bbox(annotation)

    if not bbox:
        return ""

    try:
        cropped = page.crop(bbox)
        return clean_link_label(cropped.extract_text() or "")
    except Exception:
        return ""


def extract_contacts_from_text(text: str) -> dict:
    emails = []
    phones = []
    links = []

    for match in EMAIL_RE.finditer(text or ""):
        email = match.group(0).strip()

        if email.lower() not in {item.lower() for item in emails}:
            emails.append(email)

    for match in URL_RE.finditer(text or ""):
        url = normalize_url(match.group(0))
        append_unique_link(
            links,
            classify_link_label(url),
            url,
        )

    for match in PHONE_RE.finditer(text or ""):
        phone = clean_link_label(match.group(0))
        digit_count = len(re.sub(r"\D", "", phone))

        if 10 <= digit_count <= 15 and phone not in phones:
            phones.append(phone)

    return {
        "emails": emails,
        "phones": phones,
        "links": links,
    }


def merge_contact_details(*sources: dict) -> dict:
    merged = {
        "emails": [],
        "phones": [],
        "links": [],
    }

    for source in sources:
        if not isinstance(source, dict):
            continue

        for email in as_list(source.get("emails", [])):
            email = str(email or "").strip()

            if email and email.lower() not in {
                item.lower() for item in merged["emails"]
            }:
                merged["emails"].append(email)

        for phone in as_list(source.get("phones", [])):
            phone = clean_link_label(phone)

            if phone and phone not in merged["phones"]:
                merged["phones"].append(phone)

        for link in as_list(source.get("links", [])):
            if isinstance(link, dict):
                append_unique_link(
                    merged["links"],
                    link.get("label", ""),
                    link.get("url", ""),
                )

    return merged


def extract_resume_pdf_context(file_bytes: bytes) -> dict:

    raw_text = ""
    embedded_links = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:

        for page in pdf.pages:

            text = page.extract_text()

            if text:
                raw_text += text + "\n"

            annotations = []

            annotations.extend(
                getattr(page, "hyperlinks", []) or []
            )
            annotations.extend(
                getattr(page, "annots", []) or []
            )

            for annotation in annotations:
                if not isinstance(annotation, dict):
                    continue

                url = normalize_url(
                    extract_annotation_uri(annotation)
                )

                if not url:
                    continue

                label = extract_annotation_label(
                    page,
                    annotation,
                )

                append_unique_link(
                    embedded_links,
                    label,
                    url,
                )

    if not raw_text.strip():

        raise HTTPException(
            status_code=400,
            detail="Unable to read PDF."
        )

    contact_details = merge_contact_details(
        extract_contacts_from_text(raw_text),
        {
            "links": embedded_links,
        },
    )

    linked_text = raw_text.strip()

    if embedded_links:
        linked_text += "\n\nEmbedded PDF links:\n"
        linked_text += "\n".join(
            f"- [{link['label']}]({link['url']})"
            for link in embedded_links
        )

    return {
        "text": linked_text.strip(),
        "plain_text": raw_text.strip(),
        "contact_details": contact_details,
        "embedded_links": embedded_links,
    }


def extract_text_from_pdf(file_bytes: bytes) -> str:
    return extract_resume_pdf_context(file_bytes)["text"]


def enrich_resume_data_with_pdf_context(
    resume_data: dict,
    pdf_context: dict,
) -> dict:
    if not isinstance(resume_data, dict):
        resume_data = {}

    basics = resume_data.setdefault("basics", {})
    metadata = resume_data.setdefault("metadata", {})

    contacts = pdf_context.get("contact_details", {})

    existing_contacts = {
        "emails": basics.get("emails", []),
        "phones": basics.get("phones", []),
        "links": basics.get("links", []),
    }

    merged_contacts = merge_contact_details(
        existing_contacts,
        contacts,
    )

    basics["emails"] = merged_contacts["emails"]
    basics["phones"] = merged_contacts["phones"]
    basics["links"] = merged_contacts["links"]

    embedded_links = []

    for link in as_list(metadata.get("embedded_links", [])):
        if isinstance(link, dict):
            append_unique_link(
                embedded_links,
                link.get("label", ""),
                link.get("url", ""),
            )

    for link in as_list(pdf_context.get("embedded_links", [])):
        if isinstance(link, dict):
            append_unique_link(
                embedded_links,
                link.get("label", ""),
                link.get("url", ""),
            )

    metadata["embedded_links"] = embedded_links

    if pdf_context.get("plain_text"):
        metadata["plain_resume_text"] = pdf_context["plain_text"]

    return resume_data


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


def collect_known_links(resume_data: dict) -> list[dict]:
    known_links = []

    basics = resume_data.get(
        "basics",
        {},
    )
    metadata = resume_data.get(
        "metadata",
        {},
    )

    for source in (
        basics.get("links", []),
        metadata.get("embedded_links", []),
    ):
        for link in as_list(source):
            if not isinstance(link, dict):
                continue

            append_unique_link(
                known_links,
                link.get("label", ""),
                link.get("url", ""),
            )

    return known_links


def render_linked_text(value, known_links: list[dict]) -> str:
    return annotate_links(
        safe_text(value),
        known_links,
    )


def format_email_contact(email: str) -> str:
    email = safe_text(email)

    if not email:
        return ""

    return make_anchor(
        email,
        f"mailto:{html.unescape(email)}",
    )


def format_phone_contact(phone: str) -> str:
    visible_phone = safe_text(phone)
    tel_phone = re.sub(
        r"[^\d+]",
        "",
        str(phone or ""),
    )

    if not visible_phone:
        return ""

    if not tel_phone:
        return visible_phone

    return make_anchor(
        visible_phone,
        f"tel:{tel_phone}",
    )


def format_link_contact(link: dict) -> str:
    if not isinstance(link, dict):
        return ""

    label = clean_link_label(
        link.get("label", "")
    )
    url = normalize_url(
        link.get("url", "")
    )

    if not url:
        return ""

    if not label:
        label = classify_link_label(url)

    visible_label = safe_text(label)

    if not visible_label:
        visible_label = safe_text(url)

    return make_anchor(visible_label, url)


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

    margin = 18 if density_score > 300 else 28

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
    known_links = collect_known_links(
        resume_data
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

        cleaned_headline = render_linked_text(
            headline,
            known_links,
        )

        if cleaned_headline:
            story.append(
                Paragraph(
                    cleaned_headline,
                    body_style,
                )
            )

    # =====================================================
    # CONTACT
    # =====================================================

    contact_parts = []

    emails = as_list(basics.get(
        "emails",
        [],
    ))

    phones = as_list(basics.get(
        "phones",
        [],
    ))

    location = basics.get(
        "location",
        "",
    )

    links = as_list(basics.get(
        "links",
        [],
    ))
    email_values = {
        str(email or "").strip().lower()
        for email in emails
    }
    phone_values = {
        re.sub(r"\D", "", str(phone or ""))
        for phone in phones
    }

    if emails:
        contact_parts.extend(
            [
                format_email_contact(e)
                for e in emails
                if format_email_contact(e)
            ]
        )

    if phones:
        contact_parts.extend(
            [
                format_phone_contact(p)
                for p in phones
                if format_phone_contact(p)
            ]
        )

    if location:
        contact_parts.append(
            render_linked_text(
                location,
                known_links,
            )
        )

    # =====================================================
    # LINKS
    # =====================================================

    for link in links:

        if not isinstance(link, dict):
            continue

        label = link.get(
            "label",
            "",
        )

        url = link.get(
            "url",
            "",
        )
        normalized_url = normalize_url(url)
        lowered_url = normalized_url.lower()

        if lowered_url.startswith("mailto:"):
            linked_email = lowered_url.replace(
                "mailto:",
                "",
                1,
            )

            if linked_email in email_values:
                continue

        if lowered_url.startswith("tel:"):
            linked_phone = re.sub(
                r"\D",
                "",
                lowered_url,
            )

            if linked_phone in phone_values:
                continue

        rendered = format_link_contact(
            {
                "label": label,
                "url": normalized_url,
            }
        )

        if rendered:
            contact_parts.append(rendered)

    if contact_parts:

        story.append(
            Paragraph(
                " • ".join(contact_parts),
                body_style,
                bulletText=None,
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
        # PURE STRING/TAG SECTION
        # =================================================

        if all(
            isinstance(x, str)
            for x in content
        ):

            skills = [
                render_linked_text(
                    skill,
                    known_links,
                )
                for skill in content
                if safe_text(skill)
            ]

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

            priority_keys = [
                "title",
                "name",
                "role",
                "company",
                "institution",
                "organization",
                "subtitle",
            ]

            summary_parts = []

            for key in priority_keys:

                value = item.get(key)

                if value:

                    summary_parts.append(
                        render_linked_text(
                            value,
                            known_links,
                        )
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
                    render_linked_text(
                        duration,
                        known_links,
                    )
                )

            if location:

                meta_parts.append(
                    render_linked_text(
                        location,
                        known_links,
                    )
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

            if isinstance(
                bullets,
                list,
            ):

                for bullet in bullets:

                    cleaned = render_linked_text(
                        bullet,
                        known_links,
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

                if isinstance(
                    technologies,
                    list,
                ):

                    rendered = ", ".join(
                        [
                            render_linked_text(
                                t,
                                known_links,
                            )
                            for t in technologies
                        ]
                    )

                else:

                    rendered = render_linked_text(
                        technologies,
                        known_links,
                    )

                if rendered:

                    story.append(
                        Paragraph(
                            f"<b>Technologies:</b> "
                            f"{rendered}",
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

                cleaned = render_linked_text(
                    value,
                    known_links,
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
    # BUILD PDF
    # =====================================================

    doc.build(story)

    pdf_bytes = buffer.getvalue()

    buffer.close()

    return pdf_bytes
