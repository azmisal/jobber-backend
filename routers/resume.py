from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from database.connection import get_db
from models.resume import ResumeDataSchema
from utils.pdf_parser import extract_text_from_pdf
from utils.auth_helpers import get_current_user
from models.auth import TokenData
from services.cloudinary_service import upload_pdf
from services.llm_service import parse_resume_to_json

router = APIRouter(prefix="/api/resume", tags=["Resume Management"])

@router.post("/upload")
async def upload_and_parse(file: UploadFile = File(...), current_user: TokenData = Depends(get_current_user), db=Depends(get_db)):
    file_bytes = await file.read()
    
    # 1. Upload the raw original Master to Cloudinary
    cloudinary_url = upload_pdf(file_bytes, f"master_{current_user.user_id}")
    
    # 2. Extract plain text data blocks
    raw_text = extract_text_from_pdf(file_bytes)
    
    # 3. Structure the parsing schema with LLM processing
    parsed_json = parse_resume_to_json(raw_text)
    
    profile_record = {
        "user_id": current_user.user_id,
        "cloudinary_url": cloudinary_url,
        "parsed_resume_data": parsed_json
    }
    
    # Save/Update profile database representation
    db.profiles.update_one({"user_id": current_user.user_id}, {"$set": profile_record}, upsert=True)
    return {"message": "Resume uploaded and learned.", "profile": parsed_json}

@router.get("/profile")
def get_profile(current_user: TokenData = Depends(get_current_user), db=Depends(get_db)):
    profile = db.profiles.find_one({"user_id": current_user.user_id})
    if not profile:
        return {"has_profile": False}
    return {"has_profile": True, "data": profile["parsed_resume_data"]}

@router.put("/rectify")
def rectify_profile(updated_data: ResumeDataSchema, current_user: TokenData = Depends(get_current_user), db=Depends(get_db)):
    """One-time rectification to update and verify parsed resume data in the database."""
    db.profiles.update_one(
        {"user_id": current_user.user_id},
        {"$set": {"parsed_resume_data": updated_data.model_dump()}}
    )
    return {"message": "Profile updated and verified successfully"}