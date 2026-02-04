import random
import httpx
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from firebase_admin import auth as firebase_auth

from common.database import get_db
from common.security import hash_password, verify_password, create_access_token
from common.email import send_professional_email
from .models import User, UserOTP
from .schemas import UserSignup, GoogleLogin, OTPVerify, PasswordReset

router = APIRouter(prefix="/auth", tags=["Auth"])

# --- HELPERS ---

def generate_otp():
    """Generates a secure 6-digit string OTP."""
    return f"{random.randint(100000, 999999)}"

async def get_geo_location(ip: str):
    """Fetches City, Country from IP using a public API."""
    try:
        async with httpx.AsyncClient() as client:
            # Use ip-api for free geo-lookup
            response = await client.get(f"http://ip-api.com/json/{ip}")
            data = response.json()
            if data['status'] == 'success':
                return f"{data['city']}, {data['country']}"
    except:
        pass
    return "Unknown Location"

# --- ENDPOINTS ---

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user_in: UserSignup, db: AsyncSession = Depends(get_db)):
    # Check if user exists
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create User
    new_user = User(email=user_in.email, hashed_password=hash_password(user_in.password))
    db.add(new_user)
    await db.flush() # Get the ID before committing

    # Generate Registration OTP
    otp = generate_otp()
    otp_record = UserOTP(
        user_id=new_user.id, 
        otp_code=otp, 
        purpose="verification", 
        expires_at=datetime.utcnow() + timedelta(minutes=10)
    )
    db.add(otp_record)
    await db.commit()

    # Send HTML Welcome/Registration OTP Email
    await send_professional_email(
        email_to=user_in.email,
        subject="Welcome to meiXuP - Verify Your Account",
        template_name="welcome_otp.html",
        context={"otp": otp}
    )
    return {"msg": "Registration successful. Please check your email for the verification code."}

@router.post("/verify-registration")
async def verify_registration(data: OTPVerify, db: AsyncSession = Depends(get_db)):
    user_result = await db.execute(select(User).where(User.email == data.email))
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    otp_query = select(UserOTP).where(
        (UserOTP.user_id == user.id) & 
        (UserOTP.otp_code == data.otp) & 
        (UserOTP.purpose == "verification") &
        (UserOTP.expires_at > datetime.utcnow())
    )
    result = await db.execute(otp_query)
    otp_entry = result.scalar_one_or_none()

    if not otp_entry:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    user.is_verified = True
    await db.delete(otp_entry)
    await db.commit()
    
    return {"msg": "Account verified successfully. You can now login."}

@router.post("/login")
async def login(request: Request, db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Account not verified. Please verify your email.")

    # Gather Login Details for Security Alert
    client_host = request.client.host
    user_agent = request.headers.get("user-agent", "Unknown Device")
    location = await get_geo_location(client_host)
    current_time = datetime.now().strftime("%B %d, %Y %I:%M %p")

    # Send Security Alert Email
    await send_professional_email(
        email_to=user.email,
        subject="Security Alert: New Login for meiXuP",
        template_name="security_alert.html",
        context={
            "time": current_time,
            "device": user_agent,
            "location": location
        }
    )

    token = create_access_token(user.id)
    return {"access_token": token, "token_type": "bearer"}

@router.post("/forgot-password")
async def forgot_password(email: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if user:
        otp = generate_otp()
        otp_record = UserOTP(
            user_id=user.id, 
            otp_code=otp, 
            purpose="reset", 
            expires_at=datetime.utcnow() + timedelta(minutes=10)
        )
        db.add(otp_record)
        await db.commit()
        
        await send_professional_email(
            email_to=email,
            subject="Reset Your meiXuP Password",
            template_name="reset_otp.html",
            context={
                "username": user.email.split('@')[0], 
                "email": user.email,
                "otp": otp
            }
        )
    
    return {"msg": "If this email is registered, you will receive an OTP shortly."}

@router.post("/reset-password")
async def reset_password(data: PasswordReset, db: AsyncSession = Depends(get_db)):
    user_result = await db.execute(select(User).where(User.email == data.email))
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    otp_query = select(UserOTP).where(
        (UserOTP.user_id == user.id) & 
        (UserOTP.otp_code == data.otp) & 
        (UserOTP.purpose == "reset") &
        (UserOTP.expires_at > datetime.utcnow())
    )
    result = await db.execute(otp_query)
    otp_entry = result.scalar_one_or_none()

    if not otp_entry:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    user.hashed_password = hash_password(data.new_password)
    await db.delete(otp_entry)
    await db.commit()
    
    return {"msg": "Password has been reset successfully."}

@router.post("/google-login")
async def google_login(data: GoogleLogin, db: AsyncSession = Depends(get_db)):
    try:
        decoded_token = firebase_auth.verify_id_token(data.id_token)
        email = decoded_token['email']
        fb_uid = decoded_token['uid']
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Google credentials")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        user = User(email=email, firebase_uid=fb_uid, is_verified=True, is_active=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    token = create_access_token(user.id)
    return {"access_token": token, "token_type": "bearer"}