from fastapi import FastAPI
from services.chat.router import router as chat_router

app = FastAPI()

app.include_router(chat_router, prefix="/api/v1")