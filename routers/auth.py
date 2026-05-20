from fastapi import APIRouter, Depends, HTTPException, status
from database.connection import get_db
from models.auth import UserSignup, UserLogin
from utils.auth_helpers import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/signup")
def signup(user: UserSignup, db=Depends(get_db)):
    if db.users.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="An account with this email already exists.")
    
    new_user = {
        "username": user.username,
        "email": user.email,
        "password_hash": hash_password(user.password)
    }
    result = db.users.insert_one(new_user)
    return {"message": "User registered successfully", "user_id": str(result.inserted_id)}

@router.post("/login")
def login(user: UserLogin, db=Depends(get_db)):
    db_user = db.users.find_one({"email": user.email})
    if not db_user or not verify_password(user.password, db_user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid active login email or password configuration.")
    
    token = create_access_token({"user_id": str(db_user["_id"]), "username": db_user["username"]})
    return {"access_token": token, "token_type": "bearer", "user_id": str(db_user["_id"])}