from sqlalchemy import func, select, and_, not_
from services.profiles.models import Profile
from .models import Swipe

def get_haversine_distance(lat1, lon1, lat2, lon2):
    """
    SQLAlchemy-compatible Haversine formula to calculate distance in KM.
    """
    return func.acos(
        func.sin(func.radians(lat1)) * func.sin(func.radians(lat2)) +
        func.cos(func.radians(lat1)) * func.cos(func.radians(lat2)) *
        func.cos(func.radians(lon2) - func.radians(lon1))
    ) * 6371

async def get_filtered_discovery_feed(db, user_id, lat, lon, radius_km=50):
    """
    Returns profiles within radius, excluding people already swiped.
    """
    # 1. Get IDs of people the user already swiped on
    swiped_ids_query = await db.execute(
        select(Swipe.target_id).where(Swipe.swiper_id == user_id)
    )
    swiped_ids = swiped_ids_query.scalars().all()

    # 2. Build the main discovery query
    distance_col = get_haversine_distance(lat, lon, Profile.location_lat, Profile.location_long).label("distance")
    
    query = (
        select(Profile, distance_col)
        .where(
            and_(
                Profile.user_id != user_id,
                not_(Profile.user_id.in_(swiped_ids)),
                # Distance Filter
                get_haversine_distance(lat, lon, Profile.location_lat, Profile.location_long) <= radius_km
            )
        )
        .order_by("distance")
        .limit(30)
    )
    
    result = await db.execute(query)
    return result.all()