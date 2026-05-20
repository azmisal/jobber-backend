import json
from openai import OpenAI
from config.settings import settings

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=settings.JOBBER_GROQ_API_KEY
)

def parse_resume_to_json(raw_text: str) -> dict:
    """Converts rough PDF string formats into clean schemas using structured JSON processing."""
    prompt = f"""
    You are an AI specialized in data extraction. Parse this raw resume plain text into a structured JSON file matching this schema layout cleanly:
    {{
        "summary": "Your profile summary string...",
        "skills": ["Skill1", "Skill2"],
        "experience": [
            {{
                "company": "Company Name",
                "role": "Role Title",
                "duration": "Dates active",
                "bullets": ["Action statement 1", "Action statement 2"]
            }}
        ],
        "education": ["Education details strings"]
    }}
    
    Raw text:
    {raw_text}
    """
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a precise data extractor that outputs ONLY valid JSON matching the requested schema."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

def extract_keywords(jd_text: str, existing_skills: list) -> list:
    """Identifies critical target missing keywords from the JD."""
    prompt = f"""
    Analyze the following Job Description. Identify up to 10 key technical skills or terms required.
    Ignore terms the candidate already has in this list: {existing_skills}.
    Return a JSON object containing an array of strings. Format: {{"keywords": ["keyword1", "keyword2"]}}
    
    Job Description:
    {jd_text}
    """
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a technical recruiter. Return your analysis matching the exact JSON format requested."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content).get("keywords", [])

def generate_optimization_proposals(resume_data: dict, selected_keywords: list) -> list:
    """Generates modifications for existing text to include missing keywords without altering meaning."""
    prompt = f"""
    You are an expert resume writer. Your job is to inject these keywords: {selected_keywords} into the resume data provided below.
    
    CRITICAL RULES:
    1. Do NOT fabricate experience, change meaning, or add completely new blocks of text.
    2. Only modify existing lines (summary or experience bullet points) to naturally include the keyword.
    3. Adding a keyword once across the entire document is sufficient.
    4. Return a JSON object with a list of proposed adjustments matching this exact schema:
    {{
        "proposals": [
            {{
                "id": 1,
                "section": "experience", 
                "item_index": 0, 
                "bullet_index": 1,
                "original_line": "Original bullet point text",
                "proposed_line": "Modified bullet point text containing the keyword naturally",
                "keyword_added": "The Keyword"
            }}
        ]
    }}
    
    Resume Data:
    {json.dumps(resume_data)}
    """
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You optimize resume strings. Return ONLY the JSON container with the proposals data list."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content).get("proposals", [])

def create_cover_letter(resume_data: dict, jd_text: str) -> str:
    """Generates a professional cover letter matching the candidate's core profile context."""
    prompt = f"""
    Write a concise, professional cover letter based on this resume and target job description.
    Resume: {json.dumps(resume_data)}
    Job Description: {jd_text}
    Keep it standard, clean, and compelling. Output the document text directly. Do not wrap it in JSON.
    """
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are an expert career consultant writing a professional cover letter copy."},
            {"role": "user", "content": prompt}
        ]
        # Removed json_object constraint since we want raw paragraph formatting here
    )
    return response.choices[0].message.content