from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from common.database import Base
from sqlalchemy.sql import func
import enum

class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"
    moderator = "moderator"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True) # Nullable for Google Users
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False) # OTP Check
    firebase_uid = Column(String(255), unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class UserOTP(Base):
    __tablename__ = "user_otps"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    otp_code = Column(String(6))
    purpose = Column(String(20)) # 'verification' or 'reset'
    expires_at = Column(DateTime)