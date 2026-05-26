from fastapi import APIRouter, Depends, HTTPException

from database.connection import get_db

from models.resume import (
    JDSubmission,
    KeywordSelection,
    OptimizationApprovalPayload,
)

from utils.auth_helpers import get_current_user
from models.auth import TokenData

from services.llm_service import (
    extract_keywords,
    generate_optimization_proposals,
    create_cover_letter,
)

from utils.pdf_parser import generate_pdf_bytes
from utils.resume_quality import (
    canonicalize_resume_data,
    cleanup_resume_data,
)
from services.cloudinary_service import upload_pdf

router = APIRouter(
    prefix="/api/optimize",
    tags=["Optimization Loop Engine"],
)


@router.post("/keywords")
def fetch_target_keywords(
    payload: JDSubmission,
    current_user: TokenData = Depends(
        get_current_user
    ),
    db=Depends(get_db),
):
    profile = db.profiles.find_one(
        {"user_id": current_user.user_id}
    )

    if not profile:
        raise HTTPException(
            status_code=404,
            detail=(
                "Please upload a resume first."
            ),
        )

    resume_data = profile.get(
        "parsed_resume_data",
        {}
    )
    resume_data = canonicalize_resume_data(
        resume_data
    )

    existing_skills = []

    sections = resume_data.get(
        "sections",
        []
    )

    for section in sections:

        title = str(
            section.get("title", "")
        ).lower()

        if "skill" in title:

            content = section.get(
                "content",
                []
            )

            if isinstance(content, list):
                existing_skills.extend(
                    [
                        str(x)
                        for x in content
                    ]
                )

    keywords = extract_keywords(
        payload.job_description,
        existing_skills,
        payload.model
    )

    db.profiles.update_one(
        {"user_id": current_user.user_id},
        {
            "$set": {
                "current_jd": payload.job_description
            }
        },
    )

    return {
        "keywords": keywords
    }


@router.post("/proposals")
def fetch_proposals(
    payload: KeywordSelection,
    current_user: TokenData = Depends(
        get_current_user
    ),
    db=Depends(get_db),
):
    profile = db.profiles.find_one(
        {"user_id": current_user.user_id}
    )

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Resume profile not found.",
        )

    resume_data = profile.get(
        "parsed_resume_data",
        {}
    )
    resume_data = canonicalize_resume_data(
        resume_data
    )

    proposals = (
        generate_optimization_proposals(
            resume_data,
            payload.selected_keywords,
            payload.model
        )
    )

    return {
        "proposals": proposals
    }


@router.post("/apply")
def apply_optimization_and_finalize(
    payload: OptimizationApprovalPayload,
    current_user: TokenData = Depends(
        get_current_user
    ),
    db=Depends(get_db),
):
    profile = db.profiles.find_one(
        {"user_id": current_user.user_id}
    )

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Resume profile not found.",
        )

    optimized_resume = dict(
        profile.get(
            "parsed_resume_data",
            {}
        )
    )
    optimized_resume = canonicalize_resume_data(
        optimized_resume
    )

    approved_map = {
        p.id: p
        for p in payload.proposals
        if p.id in payload.approved_ids
    }

    sections = optimized_resume.get(
        "sections",
        []
    )

    for _, prop in approved_map.items():

        section_id = prop.section_id

        matching_section = next(
            (
                s
                for s in sections
                if s.get("id")
                == section_id
            ),
            None,
        )

        if not matching_section:
            continue

        content = matching_section.get(
            "content",
            []
        )

        if not isinstance(
            content,
            list,
        ):
            continue

        if (
            prop.item_index
            >= len(content)
        ):
            continue

        item = content[prop.item_index]

        # STRING CONTENT

        if isinstance(item, str):

            content[
                prop.item_index
            ] = prop.proposed_text

            continue

        # OBJECT CONTENT

        if isinstance(item, dict):

            field_value = item.get(
                prop.field
            )

            # ARRAY FIELD

            if (
                isinstance(
                    field_value,
                    list,
                )
                and prop.field_index
                is not None
                and prop.field_index
                < len(field_value)
            ):
                field_value[
                    prop.field_index
                ] = prop.proposed_text

            # STRING FIELD

            elif isinstance(
                field_value,
                str,
            ):
                item[
                    prop.field
                ] = prop.proposed_text

    optimized_resume = cleanup_resume_data(
        optimized_resume
    )

    # GENERATE ATS PDF

    pdf_output_bytes = (
        generate_pdf_bytes(
            optimized_resume
        )
    )
    unique_filename = (
            f"{payload.output_file_name}_"
            f"{current_user.user_id}"
        )

    cloudinary_download_url = (
        upload_pdf(
            pdf_output_bytes,
            unique_filename,
        )
    )

    cover_letter = (
        create_cover_letter(
            optimized_resume,
            profile.get(
                "current_jd",
                "",
            ),
            payload.model
        )
    )

    return {
        "message": (
            "Tailored resume generated successfully."
        ),
        "file_name": unique_filename,
        "download_url": cloudinary_download_url,
        "cover_letter": cover_letter,
    }
