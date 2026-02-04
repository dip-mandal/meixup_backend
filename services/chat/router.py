from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, desc
import json
import logging
from typing import List

from common.database import get_db
from common.websocket import manager  # Master Switchboard
from common.security import decode_access_token
from services.auth.models import User
from services.profiles.models import Profile
from services.discovery.models import Match
from .models import Message, ChatRoom

logger = logging.getLogger("uvicorn")
router = APIRouter(prefix="/chat", tags=["Chat"])

# --- HTTP ENDPOINTS (Inbox & History) ---

@router.get("/rooms")
async def get_my_conversations(
    current_user: User = Depends(decode_access_token), # Or your standard JWT dep
    db: AsyncSession = Depends(get_db)
):
    """
    Fetches the list of active chat rooms for the inbox view.
    Includes the 'other' user's profile and the latest message.
    """
    # 1. Find matches involving the current user
    match_query = select(Match).where(
        or_(Match.user_one == current_user.id, Match.user_two == current_user.id)
    )
    matches_res = await db.execute(match_query)
    matches = matches_res.scalars().all()

    conversations = []

    for match in matches:
        other_user_id = match.user_two if match.user_one == current_user.id else match.user_one
        
        # 2. Get Other User Profile
        profile_res = await db.execute(select(Profile).where(Profile.user_id == other_user_id))
        other_profile = profile_res.scalar_one_or_none()
        
        # 3. Get Chat Room and Last Message
        room_res = await db.execute(select(ChatRoom).where(ChatRoom.match_id == match.id))
        room = room_res.scalar_one_or_none()
        
        last_msg = None
        if room:
            msg_query = select(Message).where(Message.room_id == room.id).order_by(desc(Message.created_at)).limit(1)
            msg_res = await db.execute(msg_query)
            last_msg = msg_res.scalar_one_or_none()

        conversations.append({
            "room_id": room.id if room else None,
            "other_user": {
                "id": other_user_id,
                "name": other_profile.full_name if other_profile else "User",
                "avatar": other_profile.profile_picture_url if other_profile else None
            },
            "last_message": {
                "text": last_msg.message_text if last_msg else "No messages yet",
                "time": last_msg.created_at if last_msg else match.created_at,
                "is_read": last_msg.is_read if last_msg else True
            }
        })

    # Sort inbox by most recent activity
    return sorted(conversations, key=lambda x: x['last_message']['time'], reverse=True)


# --- WEBSOCKET ENDPOINT (Real-time Delivery) ---

@router.websocket("/ws")
async def chat_websocket_endpoint(
    websocket: WebSocket, 
    token: str = Query(...), 
    db: AsyncSession = Depends(get_db)
):
    # 1. Authenticate the WebSocket
    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    user_id = int(payload.get("sub"))
    await manager.connect(user_id, websocket)

    try:
        while True:
            # 2. Receive message from sender
            data = await websocket.receive_text()
            msg_data = json.loads(data)
            
            # 3. Save to Database
            new_msg = Message(
                room_id=msg_data['room_id'],
                sender_id=user_id,
                recipient_id=msg_data['recipient_id'],
                message_text=msg_data.get('text'),
                media_url=msg_data.get('media_url')
            )
            db.add(new_msg)
            await db.commit()
            await db.refresh(new_msg)

            # 4. Push to Recipient in Real-time
            push_payload = {
                "type": "NEW_MESSAGE",
                "data": {
                    "id": new_msg.id,
                    "room_id": new_msg.room_id,
                    "sender_id": user_id,
                    "text": new_msg.message_text,
                    "media_url": new_msg.media_url,
                    "created_at": str(new_msg.created_at)
                }
            }
            
            await manager.send_personal_message(push_payload, msg_data['recipient_id'])

    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"Chat error for user {user_id}: {e}")
        manager.disconnect(user_id)