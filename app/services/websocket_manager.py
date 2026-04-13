from fastapi import WebSocket
from typing import Dict
import json
import logging

from app.services.proctoring_engine import proctoring_engine
from app.services.redis_client import redis_client

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str, exam_id: str):
        await websocket.accept()
        key = f"{user_id}:{exam_id}"
        self.active_connections[key] = websocket
        logger.info(f"User {user_id} connected for exam {exam_id}")
    
    def disconnect(self, user_id: str, exam_id: str):
        key = f"{user_id}:{exam_id}"
        if key in self.active_connections:
            del self.active_connections[key]
        logger.info(f"User {user_id} disconnected")
    
    async def handle_frame(self, user_id: str, exam_id: str, data: str):
        try:
            frame_data = json.loads(data)
            image_base64 = frame_data.get('image')
            
            if image_base64:
                # Analyze frame
                result = await proctoring_engine.analyze_frame(
                    user_id, exam_id, image_base64
                )
                
                # Send result back
                key = f"{user_id}:{exam_id}"
                if key in self.active_connections:
                    await self.active_connections[key].send_json(result)
                
                # If blocked, notify backend via Redis
                if result.get('is_blocked'):
                    await redis_client.publish_violation({
                        'user_id': user_id,
                        'exam_id': exam_id,
                        'violations': result['violations'],
                        'timestamp': result['timestamp']
                    })
                    
        except Exception as e:
            logger.error(f"Error handling frame: {e}")

manager = ConnectionManager()