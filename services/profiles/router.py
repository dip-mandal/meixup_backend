from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import date

from common.database import get_db
from common.deps import get_current_user
from common.storage import storage  # Our new storage utility
from services.auth.models import User
from .models import Profile

router = APIRouter(prefix="/profiles", tags=["Profiles"])

@router.put("/me")
async def update_my_profile(
    username: str = Form(...),
    full_name: Optional[str] = Form(None),
    bio: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    dob: Optional[date] = Form(None),
    profile_picture: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    # 1. Check if profile exists
    result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = result.scalar_one_or_none()

    # 2. Handle Profile Picture Upload to Cloudflare R2
    avatar_url = profile.profile_picture_url if profile else None
    if profile_picture:
        avatar_url = await storage.upload_file_direct(profile_picture, folder="avatars")

    # 3. Create or Update logic
    if not profile:
        profile = Profile(
            user_id=current_user.id,
            username=username,
            full_name=full_name,
            bio=bio,
            gender=gender,
            dob=dob,
            profile_picture_url=avatar_url
        )
        db.add(profile)
    else:
        profile.username = username
        profile.full_name = full_name
        profile.bio = bio
        profile.gender = gender
        profile.dob = dob
        profile.profile_picture_url = avatar_url
    
    await db.commit()
    return {
        "message": "Profile updated successfully", 
        "profile_picture": avatar_url,
        "username": profile.username
    }

@router.get("/me")
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.get("/search/users")
async def search_users(
    query: str, 
    limit: int = 10, 
    db: AsyncSession = Depends(get_db)
):
    """Searches for users by their full name or email (case-insensitive)."""
    search_query = select(Profile).where(
        Profile.full_name.ilike(f"%{query}%")
    ).limit(limit)
    
    result = await db.execute(search_query)
    return result.scalars().all()