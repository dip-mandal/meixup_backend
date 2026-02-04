from sqlalchemy import Column, Integer, ForeignKey, Enum, DateTime, Boolean, Index
from sqlalchemy.sql import func
from common.database import Base
import enum

class SwipeType(str, enum.Enum):
    like = "like"
    dislike = "dislike"
    super_like = "super-like"

class Swipe(Base):
    __tablename__ = "swipes"
    
    id = Column(Integer, primary_key=True, index=True)
    swiper_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    swipe_type = Column(Enum(SwipeType), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Index for faster lookup of mutual likes
    __table_args__ = (Index('idx_swiper_target', 'swiper_id', 'target_id'),)

class Match(Base):
    __tablename__ = "matches"
    
    id = Column(Integer, primary_key=True, index=True)
    user_one = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user_two = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())