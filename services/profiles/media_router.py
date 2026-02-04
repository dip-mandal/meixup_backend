from fastapi import APIRouter, Depends
from common.storage import generate_upload_url
from pydantic import BaseModel
import uuid

router = APIRouter(prefix="/media", tags=["Media"])

class UploadRequest(BaseModel):
    file_type: str # e.g., "image/jpeg"

@router.post("/request-upload")
async def get_upload_link(request: UploadRequest):
    # Generate a unique filename
    file_id = f"avatars/{uuid.uuid4()}.jpg"
    
    upload_url = generate_upload_url(file_id, request.file_type)
    
    # This is the URL the user will see later
    public_url = f"https://cdn.meixup.com/{file_id}" 
    
    return {
        "upload_url": upload_url,
        "public_url": public_url
    }