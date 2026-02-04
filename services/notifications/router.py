from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, update
from typing import List

from common.database import get_db
from common.deps import get_current_user
from services.auth.models import User
from .models import Notification

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("/")
async def get_my_notifications(
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    """Fetch the latest 50 notifications for the logged-in user."""
    query = select(Notification).where(
        Notification.recipient_id == current_user.id
    ).order_by(desc(Notification.created_at)).limit(50)
    
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/read-all")
async def mark_notifications_as_read(
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    """Mark all unread notifications as read for the current user."""
    query = update(Notification).where(
        Notification.recipient_id == current_user.id
    ).values(is_read=True)
    
    await db.execute(query)
    await db.commit()
    return {"message": "All notifications marked as read"}