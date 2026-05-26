from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pymongo.collection import Collection


def upsert_profile(
    profiles_col: Collection,
    users_col: Collection,
    *,
    user_id: str,
    username: str,
    resumeUrl: str,
    profileData: Dict[str, Any],
    userEmail: Optional[str] = None,
) -> Dict[str, Any]:
    now = datetime.utcnow()

    if not userEmail:
        user_doc = users_col.find_one({"_id": user_id}) or users_col.find_one(
            {"user_id": user_id}
        )
        if user_doc:
            userEmail = user_doc.get("email")

    if not userEmail:
        userEmail = ""

    filter_q = {"user_id": user_id}

    existing = profiles_col.find_one(filter_q)
    if existing:
        createdAt = existing.get("createdAt")
    else:
        createdAt = now

    update = {
        "$set": {
            "userEmail": userEmail,
            "username": username,
            "resumeUrl": resumeUrl,
            "profileData": profileData,
            "updatedAt": now,
        },
        "$setOnInsert": {
            "createdAt": createdAt,
        },
    }

    profiles_col.update_one(filter_q, update, upsert=True)
    return profiles_col.find_one(filter_q)

