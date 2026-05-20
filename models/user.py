"""
models/user.py — User Data Models

Pydantic models for user-related request/response validation.
Maps to the "users" collection in MongoDB.
"""

from pydantic import BaseModel, EmailStr, Field


class UserSignup(BaseModel):
    """Request model for user registration."""
    username: str = Field(..., min_length=2, max_length=50, description="Display name")
    email: EmailStr = Field(..., description="Unique email address")
    password: str = Field(..., min_length=6, description="Plain text password (hashed before storage)")


class UserLogin(BaseModel):
    """Request model for user login."""
    email: EmailStr
    password: str


class UserInDB(BaseModel):
    """Represents a user document stored in MongoDB."""
    id: str = Field(alias="_id")
    username: str
    email: str
    password_hash: str

    class Config:
        populate_by_name = True


class UserResponse(BaseModel):
    """Safe user data returned to the client (no password hash)."""
    id: str
    username: str
    email: str


class TokenResponse(BaseModel):
    """JWT token returned after successful authentication."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
