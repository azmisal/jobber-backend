from pydantic import BaseModel
from typing import List, Optional

class ExperienceItem(BaseModel):
    company: str
    role: str
    duration: str
    bullets: List[str]

class ResumeDataSchema(BaseModel):
    summary: str
    skills: List[str]
    experience: List[ExperienceItem]
    education: List[str]

class JDSubmission(BaseModel):
    job_description: str

class KeywordSelection(BaseModel):
    """Payload for the selected keywords the user wants injected."""
    selected_keywords: List[str]
    rejected_keywords: List[str] = []

class OptimizationProposal(BaseModel):
    id: int
    section: str # "summary" or "experience"
    item_index: int # Index of the experience item if applicable
    bullet_index: Optional[int] = None # Index of the bullet within that experience item
    original_line: str
    proposed_line: str
    keyword_added: str

class OptimizationApprovalPayload(BaseModel):
    approved_ids: List[int]
    proposals: List[OptimizationProposal]
    output_file_name: str