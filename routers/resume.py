from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from database.connection import get_db
from models.resume import ResumeDataSchema
from utils.pdf_parser import (
    enrich_resume_data_with_pdf_context,
    extract_resume_pdf_context,
)
from utils.resume_quality import (
    canonicalize_resume_data,
    cleanup_resume_data,
)
from utils.auth_helpers import get_current_user
from models.auth import TokenData
from services.cloudinary_service import upload_pdf
from services.llm_service import parse_resume_to_json

from utils.profile_upsert import upsert_profile


router = APIRouter(prefix="/api/resume", tags=["Resume Management"])

from fastapi import Form


@router.post("/upload")
async def upload_and_parse(
    file: UploadFile = File(...),
    model: str = Form(...),
    current_user: TokenData = Depends(get_current_user),
    db=Depends(get_db),
):
    file_bytes = await file.read()

    cloudinary_url = upload_pdf(
        file_bytes,
        f"master_{current_user.user_id}"
    )

    pdf_context = extract_resume_pdf_context(file_bytes)

    parsed_json = parse_resume_to_json(
        pdf_context["plain_text"],
        model,
        pdf_context.get("embedded_links", []),
    )
    parsed_json = enrich_resume_data_with_pdf_context(
        parsed_json,
        pdf_context,
    )
    parsed_json = cleanup_resume_data(parsed_json)

    # Persist required profile shape (single object per user)
    profiles_col = db.profiles
    users_col = db.users

    upserted = upsert_profile(
        profiles_col,
        users_col,
        user_id=current_user.user_id,
        username=current_user.username,
        resumeUrl=cloudinary_url,
        profileData=parsed_json,
    )

    return {
        "message": "Resume uploaded and learned.",
        "profile": upserted.get("profileData", parsed_json),
    }


@router.get("/profile")
def get_profile(
    current_user: TokenData = Depends(get_current_user),
    db=Depends(get_db),
):
    profile = db.profiles.find_one({"user_id": current_user.user_id})
    if not profile:
        # Compatibility with current frontend
        return {"has_profile": False}

    return {
        "has_profile": True,
        "data": profile.get("profileData") or profile.get("parsed_resume_data"),
        "resumeUrl": profile.get("resumeUrl") or profile.get("cloudinary_url"),
    }


@router.put("/rectify")
def rectify_profile(
    updated_data: ResumeDataSchema,
    current_user: TokenData = Depends(get_current_user),
    db=Depends(get_db),
):
    """Update profile parsed resume data (upsert, no duplicates)."""

    # Canonicalize but do NOT drop unknown/dynamic fields
    cleaned_data = canonicalize_resume_data(updated_data.model_dump())

    # Preserve existing resumeUrl if available
    existing = db.profiles.find_one({"user_id": current_user.user_id}) or {}
    resume_url = existing.get("resumeUrl") or existing.get("cloudinary_url") or ""

    upsert_profile(
        db.profiles,
        db.users,
        user_id=current_user.user_id,
        username=current_user.username,
        resumeUrl=resume_url,
        profileData=cleaned_data,
    )

    return {"message": "Profile updated and verified successfully"}

