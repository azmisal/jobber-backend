from pydantic import BaseModel, EmailStr

class UserSignup(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenData(BaseModel):
    user_id: str
    username: str