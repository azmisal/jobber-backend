import copy
import json
import re
from uuid import uuid4


PROJECT_TITLE_RE = re.compile(
    r"\b(projects?|team projects?|academic projects?|personal projects?|"
    r"portfolio projects?|key projects?|selected projects?)\b",
    re.IGNORECASE,
)
WHITESPACE_RE = re.compile(r"\s+")
CORE_KEYS = {
    "basics",
    "metadata",
    "sections",
    "raw_resume_text",
}
BASIC_ALIASES = {
    "full_name": (
        "full_name",
        "fullName",
        "name",
        "candidate_name",
        "candidateName",
    ),
    "headline": (
        "headline",
        "title",
        "role",
        "summary_title",
        "professional_title",
    ),
    "location": (
        "location",
        "address",
        "city",
    ),
}
CONTACT_KEYS = {
    "contact",
    "contacts",
    "contact_info",
    "contactInfo",
    "personal_info",
    "personalInfo",
}
SECTION_ALIASES = {
    "summary": "Summary",
    "profile": "Summary",
    "objective": "Summary",
    "experience": "Experience",
    "work_experience": "Experience",
    "workExperience": "Experience",
    "employment": "Experience",
    "professional_experience": "Experience",
    "professionalExperience": "Experience",
    "projects": "Projects",
    "team_projects": "Projects",
    "teamProjects": "Projects",
    "academic_projects": "Projects",
    "academicProjects": "Projects",
    "personal_projects": "Projects",
    "personalProjects": "Projects",
    "education": "Education",
    "skills": "Skills",
    "technical_skills": "Skills",
    "technicalSkills": "Skills",
    "certifications": "Certifications",
    "certificates": "Certifications",
    "awards": "Awards",
    "achievements": "Achievements",
    "publications": "Publications",
    "languages": "Languages",
}


def clean_text(value: str) -> str:
    text = str(value or "").strip()
    text = WHITESPACE_RE.sub(" ", text)
    text = text.replace(" ,", ",").replace(" .", ".")
    text = text.replace(" ;", ";").replace(" :", ":")
    text = text.replace("• •", "•")
    return text


def normalize_title(title: str) -> str:
    normalized = clean_text(title).lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized).strip()
    return normalized


def humanize_key(key: str) -> str:
    key = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(key or ""))
    key = key.replace("_", " ").replace("-", " ")
    key = WHITESPACE_RE.sub(" ", key).strip()
    return key.title() if key else "Custom"


def first_value(source: dict, aliases: tuple[str, ...]) -> str:
    for alias in aliases:
        value = source.get(alias)

        if isinstance(value, str) and value.strip():
            return clean_text(value)

    return ""


def ensure_list(value) -> list:
    if value is None or value == "":
        return []

    if isinstance(value, list):
        return value

    return [value]


def normalize_string_list(value) -> list[str]:
    values = []

    for item in ensure_list(value):
        if isinstance(item, dict):
            item = (
                item.get("value")
                or item.get("text")
                or item.get("label")
                or item.get("url")
                or ""
            )

        item = clean_text(item)

        if item and item.lower() not in {x.lower() for x in values}:
            values.append(item)

    return values


def normalize_links(value) -> list[dict]:
    links = []

    for item in ensure_list(value):
        label = ""
        url = ""

        if isinstance(item, str):
            url = clean_text(item)
            label = ""
        elif isinstance(item, dict):
            label = clean_text(
                item.get("label")
                or item.get("name")
                or item.get("title")
                or item.get("type")
                or ""
            )
            url = clean_text(
                item.get("url")
                or item.get("href")
                or item.get("link")
                or item.get("value")
                or ""
            )
        else:
            continue

        if not url:
            continue

        candidate = {
            "label": label,
            "url": url,
        }

        if (label.lower(), url.lower()) not in {
            (
                link.get("label", "").lower(),
                link.get("url", "").lower(),
            )
            for link in links
        }:
            links.append(candidate)

    return links


def merge_basics(*sources: dict) -> dict:
    basics = {
        "full_name": "",
        "headline": "",
        "emails": [],
        "phones": [],
        "location": "",
        "links": [],
    }

    for source in sources:
        if not isinstance(source, dict):
            continue

        for target, aliases in BASIC_ALIASES.items():
            if basics[target]:
                continue

            basics[target] = first_value(source, aliases)

        basics["emails"].extend(
            normalize_string_list(
                source.get("emails")
                or source.get("email")
            )
        )
        basics["phones"].extend(
            normalize_string_list(
                source.get("phones")
                or source.get("phone")
                or source.get("mobile")
            )
        )
        basics["links"].extend(
            normalize_links(
                source.get("links")
                or source.get("urls")
                or source.get("profiles")
                or source.get("websites")
            )
        )

        for key in ("linkedin", "github", "portfolio", "website"):
            if source.get(key):
                basics["links"].extend(
                    normalize_links(
                        {
                            "label": humanize_key(key),
                            "url": source.get(key),
                        }
                    )
                )

    basics["emails"] = normalize_string_list(basics["emails"])
    basics["phones"] = normalize_string_list(basics["phones"])
    basics["links"] = normalize_links(basics["links"])

    return basics


def normalize_content_item(item):
    if item is None or item == "":
        return None

    if isinstance(item, (str, int, float, bool)):
        return clean_text(item)

    if isinstance(item, list):
        values = [
            normalize_content_item(child)
            for child in item
        ]
        return [
            child
            for child in values
            if child not in (None, "", [], {})
        ]

    if isinstance(item, dict):
        normalized = {}

        for key, value in item.items():
            normalized_value = normalize_content_item(value)

            if normalized_value in (None, "", [], {}):
                continue

            normalized[str(key)] = normalized_value

        return normalized

    return clean_text(item)


def normalize_section_content(value) -> list:
    if value is None or value == "":
        return []

    if isinstance(value, list):
        raw_items = value
    elif isinstance(value, dict):
        raw_items = [value]
    else:
        raw_items = [value]

    content = []

    for item in raw_items:
        normalized = normalize_content_item(item)

        if normalized in (None, "", [], {}):
            continue

        if isinstance(normalized, list):
            content.extend(normalized)
        else:
            content.append(normalized)

    return content


def normalize_section(section, fallback_title: str = "Custom") -> dict | None:
    if section in (None, "", [], {}):
        return None

    if not isinstance(section, dict):
        content = normalize_section_content(section)
        return {
            "id": str(uuid4()),
            "title": fallback_title,
            "type": normalize_title(fallback_title) or "custom",
            "content": content,
            "raw_text": "",
        } if content else None

    title = clean_text(
        section.get("title")
        or section.get("heading")
        or section.get("name")
        or fallback_title
    )
    section_type = clean_text(
        section.get("type")
        or normalize_title(title)
        or "custom"
    )
    content_value = (
        section.get("content")
        if "content" in section
        else section.get("items")
        if "items" in section
        else section.get("entries")
        if "entries" in section
        else section.get("details")
    )

    ignored = {
        "id",
        "title",
        "heading",
        "name",
        "type",
        "content",
        "items",
        "entries",
        "details",
        "raw_text",
        "rawText",
    }

    if content_value is None:
        extra = {
            key: value
            for key, value in section.items()
            if key not in ignored
        }
        content_value = extra if extra else section.get("raw_text", "")

    content = normalize_section_content(content_value)

    return {
        "id": clean_text(section.get("id")) or str(uuid4()),
        "title": title or fallback_title,
        "type": section_type or "custom",
        "content": content,
        "raw_text": clean_text(
            section.get("raw_text")
            or section.get("rawText")
            or ""
        ),
    } if content or section.get("raw_text") or section.get("rawText") else None


def maybe_unwrap_resume_payload(data: dict) -> dict:
    if not isinstance(data, dict):
        return {}

    for key in ("resume", "resume_data", "resumeData", "data", "profile"):
        value = data.get(key)

        if isinstance(value, dict) and (
            "sections" in value
            or "basics" in value
            or any(alias in value for alias in SECTION_ALIASES)
        ):
            return value

    return data


def canonicalize_resume_data(
    resume_data: dict,
    raw_text: str = "",
) -> dict:
    if isinstance(resume_data, list):
        resume_data = {
            "sections": resume_data,
        }

    data = maybe_unwrap_resume_payload(
        copy.deepcopy(resume_data)
    )

    basics_sources = []

    if isinstance(data.get("basics"), dict):
        basics_sources.append(data.get("basics", {}))

    for key in CONTACT_KEYS:
        if isinstance(data.get(key), dict):
            basics_sources.append(data[key])

    basics_sources.append(data)

    basics = merge_basics(*basics_sources)
    sections = []

    for section in ensure_list(data.get("sections")):
        normalized = normalize_section(section)

        if normalized:
            sections.append(normalized)

    for key, value in data.items():
        if key in CORE_KEYS or key in CONTACT_KEYS:
            continue

        if key in set().union(*[set(v) for v in BASIC_ALIASES.values()]):
            continue

        if key in {
            "email",
            "emails",
            "phone",
            "phones",
            "mobile",
            "linkedin",
            "github",
            "portfolio",
            "website",
            "links",
            "urls",
            "profiles",
            "websites",
        }:
            continue

        fallback_title = SECTION_ALIASES.get(key, humanize_key(key))
        normalized = normalize_section(value, fallback_title)

        if normalized:
            sections.append(normalized)

    metadata = data.get("metadata", {})

    if not isinstance(metadata, dict):
        metadata = {}

    canonical = {
        "basics": basics,
        "sections": sections,
        "metadata": {
            "section_order": metadata.get("section_order", []),
            "parsing_confidence": metadata.get("parsing_confidence", 0.0),
            "embedded_links": metadata.get("embedded_links", []),
            "plain_resume_text": metadata.get("plain_resume_text", ""),
        },
        "raw_resume_text": clean_text(
            data.get("raw_resume_text")
            or data.get("rawText")
            or raw_text
            or ""
        ),
    }

    return cleanup_resume_data(canonical)


def is_project_section(section: dict) -> bool:
    title = str(section.get("title", ""))
    section_type = str(section.get("type", ""))
    return bool(
        PROJECT_TITLE_RE.search(title)
        or PROJECT_TITLE_RE.search(section_type)
    )


def item_fingerprint(item) -> str:
    if isinstance(item, dict):
        parts = []

        for key in (
            "title",
            "name",
            "subtitle",
            "company",
            "organization",
            "institution",
            "role",
        ):
            value = clean_text(item.get(key, ""))

            if value:
                parts.append(value.lower())

        if parts:
            return "|".join(parts)

    serialized = json.dumps(
        item,
        sort_keys=True,
        default=str,
    )
    serialized = re.sub(r"https?://\S+", "", serialized)
    serialized = re.sub(r"[^a-zA-Z0-9]+", " ", serialized).lower()
    return WHITESPACE_RE.sub(" ", serialized).strip()[:240]


def merge_unique_content(target: dict, source: dict) -> None:
    target_content = target.setdefault("content", [])
    source_content = source.get("content", [])

    if not isinstance(target_content, list):
        target_content = []
        target["content"] = target_content

    if not isinstance(source_content, list):
        return

    seen = {
        item_fingerprint(item)
        for item in target_content
        if item_fingerprint(item)
    }

    for item in source_content:
        fingerprint = item_fingerprint(item)

        if fingerprint and fingerprint in seen:
            continue

        target_content.append(item)

        if fingerprint:
            seen.add(fingerprint)

    raw_text = clean_text(source.get("raw_text", ""))

    if raw_text and raw_text not in clean_text(target.get("raw_text", "")):
        target["raw_text"] = clean_text(
            f"{target.get('raw_text', '')}\n{raw_text}"
        )


def normalize_text_fields(value):
    if isinstance(value, str):
        return clean_text(value)

    if isinstance(value, list):
        cleaned = []
        seen = set()

        for item in value:
            normalized = normalize_text_fields(item)
            fingerprint = item_fingerprint(normalized)

            if fingerprint and fingerprint in seen:
                continue

            cleaned.append(normalized)

            if fingerprint:
                seen.add(fingerprint)

        return cleaned

    if isinstance(value, dict):
        return {
            key: normalize_text_fields(child)
            for key, child in value.items()
        }

    return value


def cleanup_resume_data(resume_data: dict) -> dict:
    if not isinstance(resume_data, dict):
        return {}

    cleaned = normalize_text_fields(
        copy.deepcopy(resume_data)
    )
    sections = cleaned.get("sections", [])

    if not isinstance(sections, list):
        cleaned["sections"] = []
        return cleaned

    normalized_sections = []
    project_section = None
    sections_by_title = {}

    for section in sections:
        if not isinstance(section, dict):
            continue

        section.setdefault("id", str(uuid4()))
        section.setdefault("title", "Untitled Section")
        section.setdefault("type", "custom")
        section.setdefault("content", [])
        section.setdefault("raw_text", "")

        if not section.get("content") and not section.get("raw_text"):
            continue

        if is_project_section(section):
            if project_section is None:
                project_section = section
                project_section["title"] = "Projects"
                project_section["type"] = "projects"
                normalized_sections.append(project_section)
            else:
                merge_unique_content(project_section, section)

            continue

        title_key = normalize_title(section.get("title", ""))

        if title_key and title_key in sections_by_title:
            merge_unique_content(
                sections_by_title[title_key],
                section,
            )
            continue

        normalized_sections.append(section)

        if title_key:
            sections_by_title[title_key] = section

    cleaned["sections"] = normalized_sections

    metadata = cleaned.setdefault("metadata", {})
    metadata["section_order"] = [
        section.get("id", "")
        for section in normalized_sections
        if section.get("id")
    ]

    return cleaned
