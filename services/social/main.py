from fastapi import FastAPI
from services.social.router import router as social_router

app = FastAPI()

app.include_router(social_router, prefix="/api/v1")