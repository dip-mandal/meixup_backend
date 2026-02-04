from sqlalchemy import Column, Integer, String, Text, Enum, Date, ForeignKey, Numeric
from common.database import Base
import enum

class Gender(str, enum.Enum):
    male = "male"
    female = "female"
    non_binary = "non-binary"
    other = "other"

class Profile(Base):
    __tablename__ = "profiles"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    full_name = Column(String(100))
    bio = Column(Text)
    gender = Column(Enum(Gender))
    dob = Column(Date)
    avatar_url = Column(String(255))
    # Change Decimal(10, 8) to Numeric(10, 8)
    location_lat = Column(Numeric(10, 8))
    location_long = Column(Numeric(11, 8))
