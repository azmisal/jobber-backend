import json
from uuid import uuid4

from openai import OpenAI
from config.settings import settings

clientgroq = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=settings.JOBBER_GROQ_API_KEY,
)
clienthug = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=settings.JOBBER_GROQ_API_KEY,
)
clientopen = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=settings.JOBBER_GROQ_API_KEY,
)
clientollama = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=settings.JOBBER_GROQ_API_KEY,
)

def get_llm_client(model_id: str) -> OpenAI:

    if model_id == "groq":
        return clientgroq
    elif model_id == "huggingface":
        return clienthug
    elif model_id == "openrouter":
        return clientopen
    elif model_id == "ollama":
        return clientollama
    else:
        raise ValueError(f"Unsupported model ID: {model_id}")

def parse_resume_to_json(raw_text: str,model:str) -> dict:

    client = get_llm_client(model)

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

def extract_keywords(jd_text: str, existing_resume_data: dict,model:str) -> list:
    client = get_llm_client(model)

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
    selected_keywords: list,
    model: str  
) -> list:
    """
    Generates ATS-friendly keyword injection proposals
    while improving grammar and professionalism.
    """
    client = get_llm_client(model)

    prompt = f"""
You are an elite ATS resume optimization engine.

Your task:
Inject these keywords naturally into the resume:

TARGET KEYWORDS:
{selected_keywords}

==================================================
CRITICAL RULES
==================================================

1. Do NOT fabricate experience.

2. Do NOT change meaning.

3. Do NOT add fake tools, skills,
companies, projects, certifications,
or achievements.

4. Only modify EXISTING text.

5. Inject keywords naturally.

6. Improve:
- grammar
- spelling
- grammatical correctness
- spelling accuracy
- ATS readability
- sentence clarity
- professionalism

7. Keep ALL:
- metrics
- numbers
- technologies
- business impact
- responsibilities

8. Avoid keyword stuffing.

9. Keep sentences concise and ATS-friendly.

10. Final text must sound natural and human-written.

11. One keyword insertion across the resume is usually enough.

12. If a sentence should NOT be modified,
DO NOT create a proposal for it.

13. Correct grammatical mistakes, punctuation issues,
tense inconsistencies, typo errors, and spelling mistakes
only when necessary while preserving the original meaning.

==================================================
RETURN FORMAT
==================================================

Return ONLY valid JSON.

{{
  "proposals": [
    {{
      "id": 1,
      "section_id": "experience",
      "item_index": 0,
      "field": "bullets",
      "field_index": 0,
      "original_text": "",
      "proposed_text": "",
      "keyword_added": ""
    }}
  ]
}}

==================================================
RESUME JSON
==================================================

{json.dumps(resume_data)}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You optimize resumes for ATS systems "
                    "without changing meaning."
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

    data = json.loads(
        response.choices[0].message.content
    )

    return data.get("proposals", [])


def create_cover_letter(
    resume_data: dict,
    jd_text: str,
    model:str
) -> str:
    client = get_llm_client(model)

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