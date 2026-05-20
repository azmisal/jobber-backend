from fastapi import APIRouter, Depends, HTTPException
from database.connection import get_db
from models.resume import JDSubmission, KeywordSelection, OptimizationApprovalPayload
from utils.auth_helpers import get_current_user
from models.auth import TokenData
from services.llm_service import extract_keywords, generate_optimization_proposals, create_cover_letter
from utils.pdf_parser import generate_pdf_bytes
from services.cloudinary_service import upload_pdf

router = APIRouter(prefix="/api/optimize", tags=["Optimization Loop Engine"])

@router.post("/keywords")
def fetch_target_keywords(payload: JDSubmission, current_user: TokenData = Depends(get_current_user), db=Depends(get_db)):
    profile = db.profiles.find_one({"user_id": current_user.user_id})
    if not profile:
        raise HTTPException(status_code=404, detail="Please upload a master profile resume first.")
    
    resume_data = profile["parsed_resume_data"]
    keywords = extract_keywords(payload.job_description, resume_data.get("skills", []))
    
    # Temporarily store active target job context to avoid passing state parameters on frontend calls
    db.profiles.update_one(
        {"user_id": current_user.user_id},
        {"$set": {"current_jd": payload.job_description}}
    )
    return {"keywords": keywords}

@router.post("/proposals")
def fetch_proposals(payload: KeywordSelection, current_user: TokenData = Depends(get_current_user), db=Depends(get_db)):
    profile = db.profiles.find_one({"user_id": current_user.user_id})
    resume_data = profile["parsed_resume_data"]
    
    proposals = generate_optimization_proposals(resume_data, payload.selected_keywords)
    return {"proposals": proposals}

@router.post("/apply")
def apply_optimization_and_finalize(payload: OptimizationApprovalPayload, current_user: TokenData = Depends(get_current_user), db=Depends(get_db)):
    profile = db.profiles.find_one({"user_id": current_user.user_id})
    optimized_resume = profile["parsed_resume_data"].copy()
    
    # Process only approved text updates
    approved_map = {p.id: p for p in payload.proposals if p.id in payload.approved_ids}
    
    for prop_id, prop in approved_map.items():
        if prop.section == "summary":
            optimized_resume["summary"] = prop.proposed_line
        elif prop.section == "experience":
            idx = prop.item_index
            b_idx = prop.bullet_index
            if b_idx is not None:
                optimized_resume["experience"][idx]["bullets"][b_idx] = prop.proposed_line

    # 1. Build the newly tailored PDF layout dynamically
    pdf_output_bytes = generate_pdf_bytes(optimized_resume)
    
    # 2. Transfer content securely straight to Cloudinary bucket paths
    unique_filename = f"{payload.output_file_name}_{current_user.user_id}"
    cloudinary_download_url = upload_pdf(pdf_output_bytes, unique_filename)
    
    # 3. Formulate matching Cover Letter content
    cover_letter = create_cover_letter(optimized_resume, profile.get("current_jd", ""))
    
    return {
        "message": "Tailored resume generated safely.",
        "file_name": unique_filename,
        "download_url": cloudinary_download_url,
        "cover_letter": cover_letter
    }