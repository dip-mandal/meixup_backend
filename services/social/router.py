from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, delete
from pydantic import BaseModel
from typing import List, Optional

from common.database import get_db
from common.deps import get_current_user # Assumes your JWT dep
from services.auth.models import User
from services.notifications.models import Notification
from .models import Post, ContentType, Follow, Like, Comment

router = APIRouter(prefix="/social", tags=["Social Feed"])

# --- Schemas ---
class PostCreate(BaseModel):
    caption: Optional[str] = None
    media_url: str
    content_type: ContentType
    
class CommentCreate(BaseModel):
    content: str

# --- Endpoints ---

@router.post("/post", status_code=status.HTTP_201_CREATED)
async def create_post(
    data: PostCreate, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    new_post = Post(user_id=current_user.id, **data.model_dump())
    db.add(new_post)
    await db.commit()
    return {"message": "Post published", "post_id": new_post.id}

@router.get("/feed")
async def get_global_feed(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """The public feed of the most recent public posts."""
    query = select(Post).where(Post.is_public == True).order_by(desc(Post.created_at)).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/feed/personalized")
async def get_personalized_feed(
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    """Feed containing posts only from people the user follows."""
    # 1. Find who the user is following
    following_query = select(Follow.following_id).where(Follow.follower_id == current_user.id)
    res = await db.execute(following_query)
    following_ids = res.scalars().all()

    if not following_ids:
        return []

    # 2. Fetch those posts
    feed_query = select(Post).where(
        Post.user_id.in_(following_ids)
    ).order_by(desc(Post.created_at)).limit(50)
    
    result = await db.execute(feed_query)
    return result.scalars().all()

@router.post("/follow/{target_id}")
async def follow_user(
    target_id: int, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    if target_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    
    # Check if already following
    existing = await db.execute(
        select(Follow).where((Follow.follower_id == current_user.id) & (Follow.following_id == target_id))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already following this user")

    # Create Follow & Notification
    db.add(Follow(follower_id=current_user.id, following_id=target_id))
    db.add(Notification(
        recipient_id=target_id,
        sender_id=current_user.id,
        notification_type="follow",
        content=f"{current_user.email} started following you!"
    ))

    await db.commit()
    return {"message": "Followed successfully"}

@router.delete("/unfollow/{target_id}")
async def unfollow_user(
    target_id: int, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    query = delete(Follow).where(
        (Follow.follower_id == current_user.id) & (Follow.following_id == target_id)
    )
    result = await db.execute(query)
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Not following this user")
        
    await db.commit()
    return {"message": "Unfollowed successfully"}

@router.post("/post/{post_id}/like")
async def toggle_like(
    post_id: int, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    """Toggles a like on a post. If liked, it removes it; otherwise, it adds it."""
    # Check for existing like
    existing_like = await db.execute(
        select(Like).where((Like.user_id == current_user.id) & (Like.post_id == post_id))
    )
    like_obj = existing_like.scalar_one_or_none()

    if like_obj:
        await db.delete(like_obj)
        await db.commit()
        return {"message": "Post unliked"}
    
    # Add new like
    db.add(Like(user_id=current_user.id, post_id=post_id))
    
    # Optional: Notify post author
    post_res = await db.execute(select(Post).where(Post.id == post_id))
    post = post_res.scalar_one()
    if post.user_id != current_user.id:
        db.add(Notification(
            recipient_id=post.user_id,
            sender_id=current_user.id,
            notification_type="like",
            content="liked your post!"
        ))
    
    await db.commit()
    return {"message": "Post liked"}

@router.post("/post/{post_id}/comment")
async def add_comment(
    post_id: int,
    data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Adds a comment to a specific post."""
    new_comment = Comment(
        post_id=post_id,
        user_id=current_user.id,
        content=data.content
    )
    db.add(new_comment)
    await db.commit()
    return {"message": "Comment added", "comment_id": new_comment.id}
