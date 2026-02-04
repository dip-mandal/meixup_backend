from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services.auth.router import router as auth_router
from services.profiles.router import router as profile_router
from services.discovery.router import router as discovery_router
from services.social.router import router as social_router

app = FastAPI(title="meiXuP Master API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Version 1 API Routes
app.include_router(auth_router, prefix="/api/v1")
app.include_router(profile_router, prefix="/api/v1")
app.include_router(discovery_router, prefix="/api/v1") # dating logic
app.include_router(social_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Welcome to meiXuP API v1"}