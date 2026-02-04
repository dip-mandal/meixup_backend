import firebase_admin
from firebase_admin import credentials
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from common.config import settings

# --- Import All Service Routers ---
from services.auth.router import router as auth_router
from services.profiles.router import router as profile_router
from services.profiles.search_router import router as search_router # Added
from services.social.router import router as social_router
from services.discovery.router import router as discovery_router
from services.notifications.router import router as notification_router
from services.notifications.ws_router import router as ws_router
from services.chat.router import router as chat_router # Added

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

# --- Lifespan Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Firebase Admin
    try:
        logger.info("Initializing Firebase Admin SDK...")
        firebase_admin.get_app()
    except ValueError:
        try:
            cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_PATH)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin successfully initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
    
    yield
    # Shutdown logic (cleanup database pools or storage connections)
    logger.info("Shutting down meiXuP Master API...")

app = FastAPI(
    title="meiXuP Master API",
    description="Unified Backend for meiXuP Social & Dating Platform",
    version="1.1.0",
    lifespan=lifespan
)

# --- CORS Configuration ---
# Replace "*" with specific domains (e.g., ["http://localhost:3000"]) in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Router Inclusions ---
# Prefixing all routes with /api/v1 for version control
app.include_router(auth_router, prefix="/api/v1")
app.include_router(profile_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1") # Search logic
app.include_router(social_router, prefix="/api/v1") # Posts, Likes, Follows
app.include_router(discovery_router, prefix="/api/v1") # Dating Swipe logic
app.include_router(notification_router, prefix="/api/v1") # HTTP Notifications
app.include_router(ws_router, prefix="/api/v1") # Real-time Notification Socket
app.include_router(chat_router, prefix="/api/v1") # Real-time Chat & WS

@app.get("/", tags=["Health"])
async def health_check():
    return {
        "status": "meiXuP API is fully operational",
        "version": "1.1.0",
        "services": [
            "Auth", "Profiles", "Social", "Discovery", 
            "Chat (WS)", "Notifications (WS)", "Search"
        ],
        "firebase_status": "initialized"
    }
    
