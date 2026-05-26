import json
import re

from openai import OpenAI
from config.settings import settings
from utils.resume_quality import canonicalize_resume_data


# =====================================================
# LLM CONFIG
# =====================================================

LLM_CONFIGS = {
    "groq": {
        "client": OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=settings.JOBBER_GROQ_API_KEY,
        ),
        "model": "llama-3.3-70b-versatile",
    },

    "huggingface": {
        "client": OpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=settings.HUGGINGFACE_API_KEY,
        ),
        "model": "meta-llama/Llama-3.3-70B-Instruct",
    },

    "openrouter": {
        "client": OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
        ),
        "model": "meta-llama/llama-3.3-70b-instruct",
    },
    "ollama": {
        "client": OpenAI(
            base_url=f"{settings.OLLAMA_BASE_URL}/v1",
            api_key="ollama",
        ),
        "model": "llama3.1:8b",

    },
}


def get_llm(model_id: str):

    config = LLM_CONFIGS.get(model_id)

    if not config:
        raise ValueError(
            f"Unsupported model ID: {model_id}"
        )

    return (
        config["client"],
        config["model"]
    )


# =====================================================
# CLEANING HELPERS
# =====================================================

def clean_resume_sentence(text: str) -> str:

    text = str(text or "").strip()

    text = re.sub(r"\s+", " ", text)

    text = text.replace(" ,", ",")
    text = text.replace(" .", ".")
    text = text.replace(" ;", ";")
    text = text.replace(" :", ":")

    return text


def normalize_optimization_proposals(
    proposals: list
) -> list:

    normalized = []
    seen = set()

    for proposal in proposals:

        if not isinstance(proposal, dict):
            continue

        if "item_index" not in proposal and "content_index" in proposal:
            proposal["item_index"] = proposal.get("content_index")

        if "item_index" not in proposal and "itemIndex" in proposal:
            proposal["item_index"] = proposal.get("itemIndex")

        if "field_index" not in proposal and "bullet_index" in proposal:
            proposal["field_index"] = proposal.get("bullet_index")

        if "field_index" not in proposal and "fieldIndex" in proposal:
            proposal["field_index"] = proposal.get("fieldIndex")

        if "section_id" not in proposal and "sectionId" in proposal:
            proposal["section_id"] = proposal.get("sectionId")

        if "original_text" not in proposal and "original_line" in proposal:
            proposal["original_text"] = proposal.get("original_line")

        if "proposed_text" not in proposal and "proposed_line" in proposal:
            proposal["proposed_text"] = proposal.get("proposed_line")

        original = clean_resume_sentence(
            proposal.get("original_text", "")
        )

        proposed = clean_resume_sentence(
            proposal.get("proposed_text", "")
        )

        if not original or not proposed:
            continue

        if original == proposed:
            continue

        if proposal.get("section_id") in (None, ""):
            continue

        try:
            proposal["item_index"] = int(proposal.get("item_index"))
        except (TypeError, ValueError):
            continue

        if proposal.get("field_index") not in (None, ""):
            try:
                proposal["field_index"] = int(proposal.get("field_index"))
            except (TypeError, ValueError):
                proposal["field_index"] = None

        key = (
            proposal.get("section_id"),
            proposal.get("item_index"),
            proposal.get("field"),
            proposal.get("field_index"),
            original.lower(),
        )

        if key in seen:
            continue

        seen.add(key)

        proposal.setdefault(
            "id",
            len(normalized) + 1,
        )
        proposal.setdefault(
            "field",
            "bullets",
        )
        proposal.setdefault(
            "field_index",
            None,
        )
        proposal["original_text"] = original
        proposal["proposed_text"] = proposed

        proposal["keyword_added"] = (
            clean_resume_sentence(
                proposal.get(
                    "keyword_added",
                    ""
                )
            )
            or "Grammar/clarity"
        )

        normalized.append(proposal)

    return normalized


# =====================================================
# PARSE RESUME
# =====================================================

def parse_resume_to_json(
    raw_text: str,
    model: str,
    embedded_links: list | None = None,
) -> dict:

    client, model_name = get_llm(model)

    link_hints = embedded_links or []
    prompt = f"""
You are a universal resume reconstruction engine.

Parse the resume accurately.
Do not rewrite or optimize content during parsing.

Return ONLY valid JSON using this exact dynamic schema:

{{
  "basics": {{
    "full_name": "",
    "headline": "",
    "emails": [],
    "phones": [],
    "location": "",
    "links": [
      {{
        "label": "",
        "url": ""
      }}
    ]
  }},
  "sections": [
    {{
      "id": "",
      "title": "",
      "type": "",
      "content": [
        "plain string item",
        {{
          "title": "",
          "subtitle": "",
          "duration": "",
          "location": "",
          "bullets": [],
          "technologies": [],
          "links": [
            {{
              "label": "",
              "url": ""
            }}
          ]
        }}
      ],
      "raw_text": ""
    }}
  ],
  "metadata": {{
    "section_order": [],
    "parsing_confidence": 0.0
  }},
  "raw_resume_text": ""
}}

Rules:
- Always return "basics", "sections", "metadata", and "raw_resume_text".
- Put every resume section inside sections[]. Do not create top-level keys
  like experience, education, projects, skills, awards, etc.
- Section content must be a list. Each item may be either a string or a dynamic
  object with any keys needed for that profession/resume.
- Preserve unknown fields inside the relevant content object instead of
  dropping them.
- Put project-specific links inside the matching project item, not basics.
- Put contact/profile links in basics.links only when they belong to the
  candidate header.

RESUME:
{raw_text}

PDF LINKS:
{json.dumps(link_hints)}
"""

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a universal resume parser. "
                    "Return ONLY valid JSON."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        response_format={
            "type": "json_object"
        },
        temperature=0.1,
    )

    parsed = json.loads(
        response.choices[0].message.content
    )

    return canonicalize_resume_data(
        parsed,
        raw_text,
    )


# =====================================================
# KEYWORD EXTRACTION
# =====================================================

def extract_keywords(
    jd_text: str,
    existing_resume_data: dict,
    model: str,
) -> list:

    client, model_name = get_llm(model)

    prompt = f"""
You are an ATS keyword extraction engine.

Extract:
- skills
- tools
- technologies
- certifications
- qualifications
- domain keywords

RULES:
1. Maximum 15 keywords
2. No duplicates
3. Compact keywords only
4. Return ONLY JSON

JOB DESCRIPTION:
{jd_text}

RESUME:
{json.dumps(existing_resume_data)}
"""

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": (
                    "You extract ATS keywords. "
                    "Return ONLY valid JSON."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        response_format={
            "type": "json_object"
        },
        temperature=0.1,
    )

    parsed = json.loads(
        response.choices[0].message.content
    )

    return parsed.get("keywords", [])


# =====================================================
# RESUME OPTIMIZATION
# =====================================================

def generate_optimization_proposals(
    resume_data: dict,
    selected_keywords: list,
    model: str,
) -> list:

    client, model_name = get_llm(model)

    prompt = f"""
You are an elite ATS resume optimization engine.

Improve:
- grammar
- spelling
- punctuation
- ATS readability
- clarity
- professionalism
- quantified impact
- action verbs

Inject keywords naturally.

TARGET KEYWORDS:
{selected_keywords}

RULES:
1. Do NOT fabricate experience
2. Do NOT change meaning
3. Do NOT add fake skills/tools/projects
4. Only modify existing text
5. Preserve metrics and technologies
6. Avoid repetition
7. Avoid keyword stuffing
8. Keep sentences concise
9. Correct grammar whenever necessary
10. Use stronger action verbs where truthful
11. Improve quantified impact visibility
12. Return ONLY valid JSON

Return this exact shape:
{{
  "proposals": [
    {{
      "id": 1,
      "section_id": "existing-section-id",
      "item_index": 0,
      "field": "bullets",
      "field_index": 0,
      "original_text": "",
      "proposed_text": "",
      "keyword_added": "Grammar/clarity"
    }}
  ]
}}

Use the exact section_id and item_index from the resume JSON. For string
content items, use field "content" and field_index null. For object string
fields, use that field name and field_index null. For array fields like
bullets, use the field name and the array index.

RESUME:
{json.dumps(resume_data)}
"""

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": (
                    "You optimize resumes for ATS "
                    "without changing meaning."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        response_format={
            "type": "json_object"
        },
        temperature=0.2,
    )

    data = json.loads(
        response.choices[0].message.content
    )

    return normalize_optimization_proposals(
        data.get("proposals", [])
    )


# =====================================================
# COVER LETTER
# =====================================================

def create_cover_letter(
    resume_data: dict,
    jd_text: str,
    model: str,
) -> str:

    client, model_name = get_llm(model)

    prompt = f"""
Write a professional cover letter.

RULES:
1. Keep it concise
2. Keep it professional
3. Match resume with job description
4. No fake claims
5. No markdown

RESUME:
{json.dumps(resume_data)}

JOB DESCRIPTION:
{jd_text}
"""

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert cover letter writer."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.3,
    )

    return response.choices[0].message.content
