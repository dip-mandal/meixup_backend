from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    # --- App Info ---
    PROJECT_NAME: str = "meiXuP"
    API_V1_STR: str = "/api/v1"
    
    # --- Database ---
    MYSQL_URL: str
    REDIS_URL: str
    
    # --- Security ---
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    # Set to 30 days so users don't have to login constantly (better UX)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30 
    
    # --- Cloudflare R2 ---
    R2_BUCKET_NAME: str
    R2_ACCOUNT_ID: str
    R2_ACCESS_KEY: str
    R2_SECRET_KEY: str

    # --- SMTP Email Service (NEW) ---
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    # You can also add these if you want to change providers later
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"

    # --- Firebase Admin ---
    # Path to your firebase-service-account.json file
    FIREBASE_SERVICE_ACCOUNT_PATH: str = "firebase-adminsdk.json"

    model_config = SettingsConfigDict(
        env_file=".env", 
        case_sensitive=True, 
        extra='ignore'
    )

@lru_cache
def get_settings():
    return Settings()

# Use the function to get settings
settings = get_settings()