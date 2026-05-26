from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProfileModel(BaseModel):
    """Persistent profile model.

    Note: `profileData` is intentionally dynamic to preserve unknown parsed
    resume fields.
    """

    model_config = ConfigDict(extra="allow")

    userEmail: str
    username: str
    resumeUrl: str
    profileData: Dict[str, Any]
    createdAt: datetime
    updatedAt: datetime


class ProfileUpsertRequest(BaseModel):
    """Request to upsert profile."""

    model_config = ConfigDict(extra="allow")

    resumeUrl: str
    profileData: Dict[str, Any]


class ProfileUpsertResponse(BaseModel):
    message: str
    profile: ProfileModel


class HistoryEntryModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    userEmail: str
    companyName: str
    resumeName: str
    generatedResumeUrl: str

    originalJobDescription: str
    selectedKeywords: List[str]
    optimizationProposals: List[Dict[str, Any]]

    generatedAt: datetime
    sourceResumeProfileId: str


class HistoryCreateRequest(BaseModel):
    """
    Request for persisting a generated resume history entry.

    Frontend should send:
    - companyName as manual fallback
    - originalJobDescription and selectedKeywords (source of truth)
    - resumeName (output filename)

    Backend will still attempt to extract companyName from JD and override if
    high confidence.
    """

    model_config = ConfigDict(extra="allow")

    companyName: str
    resumeName: str

    originalJobDescription: str
    selectedKeywords: List[str]


class HistoryDetailResponse(BaseModel):
    history: HistoryEntryModel
    linkedProfile: Optional[Dict[str, Any]] = None


class HistoryListItem(BaseModel):
    userEmail: str
    companyName: str
    resumeName: str
    generatedAt: datetime
    keywordCount: int
    generatedResumeUrl: str
    historyId: str


class HistoryListResponse(BaseModel):
    items: List[HistoryListItem]

