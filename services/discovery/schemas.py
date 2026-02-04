from pydantic import BaseModel, Field
from .models import SwipeType

class SwipeRequest(BaseModel):
    target_id: int = Field(..., description="The ID of the user being swiped on")
    swipe_type: SwipeType = Field(..., description="Action: like, dislike, or super-like")

    model_config = {
        "json_schema_extra": {
            "example": {
                "target_id": 2,
                "swipe_type": "like"
            }
        }
    }