from fastapi import FastAPI
from services.auth.router import router as auth_router

app = FastAPI(title="meiXuP Auth Service")

# Include the auth routes
app.include_router(auth_router)

@app.get("/")
async def root():
    return {"message": "Auth Service is Running"}