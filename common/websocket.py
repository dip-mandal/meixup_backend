from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Any, List
import logging
import asyncio

# Setup uvicorn logging for visibility in your terminal
logger = logging.getLogger("uvicorn")

class ConnectionManager:
    def __init__(self):
        # Maps user_id (int) to their active WebSocket connection
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        """Accepts the connection and stores it in the active registry."""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"🚀 User {user_id} connected. Active connections: {len(self.active_connections)}")

    def disconnect(self, user_id: int):
        """Removes the connection from the registry safely."""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"🔌 User {user_id} disconnected. Active connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: Dict[str, Any], user_id: int):
        """
        Sends a JSON payload to a specific user.
        If the connection is broken, it cleans up the registry automatically.
        """
        websocket = self.active_connections.get(user_id)
        if websocket:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"❌ Failed to send to User {user_id}: {e}")
                self.disconnect(user_id)

    async def broadcast(self, message: Dict[str, Any]):
        """Sends a message to every currently online user."""
        # list(keys) prevents 'dictionary changed size' errors during iteration
        active_user_ids = list(self.active_connections.keys())
        
        # Using gather allows sending to all users concurrently rather than one by one
        tasks = [self.send_personal_message(message, uid) for uid in active_user_ids]
        if tasks:
            await asyncio.gather(*tasks)

    def is_user_online(self, user_id: int) -> bool:
        """Utility to check if a specific user is currently active."""
        return user_id in self.active_connections

# Single global instance to be used across Discovery, Chat, and Notifications
manager = ConnectionManager()