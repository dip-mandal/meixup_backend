from fastapi import FastAPI
from services.search.router import router as search_router

app = FastAPI()

app.include_router(search_router, prefix="/api/v1")