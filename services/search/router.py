from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from common.database import get_db
from services.profiles.models import Profile
from services.social.models import Post
from typing import List

router = APIRouter(prefix="/search", tags=["Search"])

@router.get("/users")
async def search_users(q: str, limit: int = 10, db: AsyncSession = Depends(get_db)):
    """Search for users by username or full name"""
    query = select(Profile).where(
        or_(
            Profile.username.ilike(f"%{q}%"),
            Profile.full_name.ilike(f"%{q}%")
        )
    ).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/posts")
async def search_posts(q: str, limit: int = 10, db: AsyncSession = Depends(get_db)):
    """Search for posts by caption keywords"""
    query = select(Post).where(
        Post.caption.ilike(f"%{q}%")
    ).order_by(Post.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()