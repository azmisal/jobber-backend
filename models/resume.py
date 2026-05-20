from pydantic import BaseModel
from typing import List, Dict, Any


class ResumeLink(BaseModel):
    label: str = ""
    url: str = ""


class ResumeBasics(BaseModel):
    full_name: str = ""
    headline: str = ""
    emails: List[str] = []
    phones: List[str] = []
    location: str = ""
    links: List[ResumeLink] = []


class ResumeSection(BaseModel):
    id: str
    title: str
    type: str
    content: List[Any] = []
    raw_text: str = ""


class ResumeMetadata(BaseModel):
    section_order: List[str] = []
    parsing_confidence: float = 0.0


class ResumeDataSchema(BaseModel):
    basics: ResumeBasics
    sections: List[ResumeSection]
    metadata: ResumeMetadata
    raw_resume_text: str = ""


class JDSubmission(BaseModel):
    job_description: str


class KeywordSelection(BaseModel):
    selected_keywords: List[str]
    rejected_keywords: List[str] = []


class OptimizationProposal(BaseModel):
    id: int
    section_id: str
    content_index: int
    original_text: str
    proposed_text: str
    keyword_added: str


class OptimizationApprovalPayload(BaseModel):
    approved_ids: List[int]
    proposals: List[OptimizationProposal]
    output_file_name: str