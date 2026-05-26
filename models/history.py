from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ResumeHistoryProposal(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int

    # Backend optimization proposal uses these fields in current codebase
    section_id: Optional[str] = None
    item_index: Optional[int] = None
    field: Optional[str] = None
    field_index: Optional[int] = None

    original_text: str = ""
    proposed_text: str = ""
    keyword_added: str = ""


class CreateHistoryRequest(BaseModel):
    """Request payload for persisting resume generation history."""

    model_config = ConfigDict(extra="allow")

    # Manual fallback company name. Backend may override using heuristics.
    companyName: str = ""

    resumeName: str
    generatedResumeUrl: str

    originalJobDescription: str
    selectedKeywords: List[str] = []

    optimizationProposals: List[Dict[str, Any]] = []

    sourceResumeProfileId: str

    # Client may pass explicitly; backend will set generatedAt server-side.
    generatedAt: Optional[datetime] = None


class HistoryListItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    historyId: str
    companyName: str
    resumeName: str
    generatedAt: datetime
    keywordCount: int
    generatedResumeUrl: str


class HistoryDetailResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    history: Dict[str, Any]
    linkedProfile: Optional[Dict[str, Any]] = None

