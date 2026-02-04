from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from common.websocket import manager
from common.security import decode_access_token # Verify this helper exists in your security.py
import logging

logger = logging.getLogger("uvicorn")
router = APIRouter(prefix="/ws", tags=["WebSockets"])

@router.websocket("/connect")
async def websocket_endpoint(
    websocket: WebSocket, 
    token: str = Query(..., description="JWT Access Token for authentication")
):
    """
    The main entry point for real-time communication.
    Authenticates the user via token and maintains a persistent connection.
    """
    # 1. Decode and Validate Token
    try:
        payload = decode_access_token(token)
        # Extract user_id from the 'sub' claim (usually stored as a string in JWT)
        user_id_str = payload.get("sub")
        
        if not user_id_str:
            logger.warning("WebSocket connection rejected: Missing subject in token.")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
            
        user_id = int(user_id_str)
        
    except Exception as e:
        logger.error(f"WebSocket Auth Failed: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 2. Add to Connection Manager
    await manager.connect(user_id, websocket)
    
    try:
        # 3. Maintain Connection Loop
        while True:
            # We wait for messages from the client (pings or chat messages)
            # receive_json allows the client to send structured data
            data = await websocket.receive_json()
            
            # For now, we just log it. Later, this can handle "Typing..." indicators
            logger.info(f"Received from user {user_id}: {data}")
            
    except WebSocketDisconnect:
        # 4. Clean up on disconnect
        manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket Loop Error for user {user_id}: {e}")
        manager.disconnect(user_id)