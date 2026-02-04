from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List

from common.database import get_db
from common.deps import get_current_user
from services.auth.models import User
from .models import Profile

router = APIRouter(prefix="/search", tags=["Search"])

@router.get("/users")
async def search_users(
    q: str = Query(..., min_length=2, description="Search by name or email"),
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Finds users where their name or email contains the search string.
    """
    # Search in Profile (name) and User (email)
    query = (
        select(Profile)
        .join(User, Profile.user_id == User.id)
        .where(
            or_(
                Profile.full_name.ilike(f"%{q}%"),
                User.email.ilike(f"%{q}%")
            )
        )
        .limit(limit)
    )
    
    result = await db.execute(query)
    profiles = result.scalars().all()
    
    return profiles