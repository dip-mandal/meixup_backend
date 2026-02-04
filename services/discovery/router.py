from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, not_, func

from common.database import get_db
from common.deps import get_current_user
from common.websocket import manager  # Real-time manager
from services.auth.models import User
from services.profiles.models import Profile
from services.notifications.models import Notification
from .models import Swipe, Match, SwipeType
from .schemas import SwipeRequest

router = APIRouter(prefix="/dating", tags=["Dating"])

# --- HELPERS ---

def get_haversine_distance(lat1, lon1, lat2, lon2):
    """Calculates the distance in KM between two points on Earth."""
    return func.acos(
        func.sin(func.radians(lat1)) * func.sin(func.radians(lat2)) +
        func.cos(func.radians(lat1)) * func.cos(func.radians(lat2)) *
        func.cos(func.radians(lon2) - func.radians(lon1))
    ) * 6371

# --- ENDPOINTS ---

@router.get("/feed")
async def get_discovery_feed(
    radius_km: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns a list of potential matches within a specific radius."""
    # 1. Get current user's location
    user_profile_res = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    user_profile = user_profile_res.scalar_one_or_none()

    if not user_profile or user_profile.location_lat is None:
        raise HTTPException(status_code=400, detail="Update your location in profile first.")

    # 2. Exclude users already swiped on
    swiped_query = await db.execute(select(Swipe.target_id).where(Swipe.swiper_id == current_user.id))
    swiped_ids = swiped_query.scalars().all()

    # 3. Build query with distance calculation
    distance_col = get_haversine_distance(
        user_profile.location_lat, user_profile.location_long, 
        Profile.location_lat, Profile.location_long
    ).label("distance")

    query = (
        select(Profile, distance_col)
        .where(
            and_(
                Profile.user_id != current_user.id,
                not_(Profile.user_id.in_(swiped_ids)),
                get_haversine_distance(
                    user_profile.location_lat, user_profile.location_long, 
                    Profile.location_lat, Profile.location_long
                ) <= radius_km
            )
        )
        .order_by("distance").limit(30)
    )

    result = await db.execute(query)
    feed_data = result.all()

    return [{**p.Profile.__dict__, "distance_km": round(p.distance, 2)} for p in feed_data]


@router.post("/swipe")
async def perform_swipe(
    data: SwipeRequest, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    """Records a swipe and triggers match logic if applicable."""
    if data.target_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot swipe on yourself.")

    # 1. Record the Swipe
    new_swipe = Swipe(swiper_id=current_user.id, target_id=data.target_id, swipe_type=data.swipe_type)
    db.add(new_swipe)

    # 2. Match Check
    if data.swipe_type in [SwipeType.like, SwipeType.super_like]:
        match_check = await db.execute(
            select(Swipe).where(
                and_(
                    Swipe.swiper_id == data.target_id,
                    Swipe.target_id == current_user.id,
                    Swipe.swipe_type.in_([SwipeType.like, SwipeType.super_like])
                )
            )
        )
        
        if match_check.scalar_one_or_none():
            # A. Database: Create Match
            new_match = Match(user_one=current_user.id, user_two=data.target_id)
            db.add(new_match)

            # B. Database: Create Notifications
            notif_current = Notification(
                recipient_id=current_user.id,
                title="New Match! 🎉",
                content="You matched with a new user! Start a conversation now.",
                notification_type="match"
            )
            notif_target = Notification(
                recipient_id=data.target_id,
                title="New Match! 🎉",
                content="Someone just matched with you on meiXuP!",
                notification_type="match"
            )
            db.add_all([notif_current, notif_target])
            
            # C. Real-Time: WebSocket Push
            match_payload = {
                "type": "NEW_MATCH",
                "data": {
                    "match_id": data.target_id,
                    "message": "It's a match! 🎉"
                }
            }
            # Notify both users instantly
            await manager.send_personal_message(match_payload, current_user.id)
            await manager.send_personal_message(match_payload, data.target_id)

            await db.commit()
            return {"status": "match", "message": "It's a match!", "target_id": data.target_id}

    await db.commit()
    return {"status": "recorded", "message": f"{data.swipe_type} recorded."}
