import json
from uuid import uuid4

from openai import OpenAI
from config.settings import settings

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=settings.JOBBER_GROQ_API_KEY,
)


def parse_resume_to_json(raw_text: str) -> dict:

    prompt = f"""
You are a universal resume reconstruction engine.

DO NOT summarize heavily.

==================================================
RULES
==================================================

1. Preserve ALL sections.

2. Detect section headings dynamically.

3. Preserve:
- names
- bullets
- descriptions
- metrics
- dates
- achievements
- skills
- technologies
- proficiency levels
- links
- certifications
- projects
- awards
- publications

4. IMPORTANT:
Skills should remain compact.

GOOD:
[
  "React",
  "Node.js",
  "English - Fluent",
  "German - Intermediate"
]

BAD:
[
  {{
    "skill": "React",
    "description": "Frontend framework"
  }}
]

5. If entries are simple names/tags:
keep them as plain strings.

6. ONLY create objects if structured data exists.

7. Preserve unknown/custom sections.

8. Preserve original order.

9. Return ONLY valid JSON.

==================================================
OUTPUT FORMAT
==================================================

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
      "content": [],
      "raw_text": ""
    }}
  ],

  "metadata": {{
    "section_order": [],
    "parsing_confidence": 0.0
  }},

  "raw_resume_text": ""
}}

==================================================
RESUME
==================================================

{raw_text}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
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
        response_format={"type": "json_object"},
        temperature=0.1,
    )

    parsed = json.loads(
        response.choices[0].message.content
    )

    parsed.setdefault("basics", {})
    parsed.setdefault("sections", [])
    parsed.setdefault("metadata", {})
    parsed.setdefault("raw_resume_text", raw_text)

    for section in parsed["sections"]:

        if not section.get("id"):
            section["id"] = str(uuid4())

    return parsed

def extract_keywords(jd_text: str, existing_resume_data: dict) -> list:

    prompt = f"""
You are an ATS keyword extraction engine.

Extract the most important:
- skills
- tools
- technologies
- qualifications
- certifications
- competencies
- domain keywords

from this job description.

RULES:
1. Return maximum 15 keywords
2. Avoid duplicates
3. Keep keywords compact
4. No explanations
5. Return ONLY JSON

JOB DESCRIPTION:
{jd_text}

RESUME DATA:
{json.dumps(existing_resume_data)}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
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
        response_format={"type": "json_object"},
        temperature=0.1,
    )

    parsed = json.loads(
        response.choices[0].message.content
    )

    return parsed.get("keywords", [])

def generate_optimization_proposals(
    resume_data: dict,
    selected_keywords: list
) -> list:

    prompt = f"""
You are an elite ATS resume optimization engine.

Your task:
Inject these keywords naturally into the resume.

KEYWORDS:
{selected_keywords}

RULES:
1. NEVER fabricate fake experience
2. NEVER invent projects
3. NEVER change meaning
4. ONLY improve existing content
5. Preserve professionalism
6. Preserve truthfulness
7. Make wording ATS optimized
8. Return ONLY JSON

RETURN FORMAT:

{{
  "proposals": [
    {{
      "id": 1,
      "section_id": "section-id",
      "content_index": 0,
      "original_text": "",
      "proposed_text": "",
      "keyword_added": ""
    }}
  ]
}}

RESUME:
{json.dumps(resume_data)}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You optimize resumes for ATS systems. "
                    "Return ONLY JSON."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

    parsed = json.loads(
        response.choices[0].message.content
    )

    return parsed.get("proposals", [])

def create_cover_letter(
    resume_data: dict,
    jd_text: str
) -> str:

    prompt = f"""
Write a professional cover letter.

RULES:
1. Keep it concise
2. Keep it professional
3. Match candidate profile with job description
4. No fake claims
5. No markdown

RESUME:
{json.dumps(resume_data)}

JOB DESCRIPTION:
{jd_text}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
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