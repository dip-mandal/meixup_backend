from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# --- Input Schemas (Request Bodies) ---

class UserSignup(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)

class GoogleLogin(BaseModel):
    id_token: str

class OTPVerify(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)

class PasswordReset(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8)

# --- Output Schemas (Responses) ---

class Token(BaseModel):
    access_token: str
    token_type: str

class Msg(BaseModel):
    msg: str

class TokenData(BaseModel):
    user_id: Optional[int] = None
    
