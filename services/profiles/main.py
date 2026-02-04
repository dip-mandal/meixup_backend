from fastapi import FastAPI
from services.profiles.router import router as profile_router
from services.profiles.media_router import router as media_router

# Create a new instance of FastAPI
app = FastAPI()

# Add this line below your auth_router inclusion
app.include_router(profile_router)
app.include_router(media_router)