import redis.asyncio as redis
import json
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.client = None
    
    async def connect(self):
        self.client = await redis.from_url(
            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
            decode_responses=True
        )
        logger.info("Connected to Redis")
    
    async def publish_violation(self, violation_data: dict):
        """Publish violation to backend"""
        if self.client:
            await self.client.lpush('violation_queue', json.dumps(violation_data))
            logger.info(f"Violation published: {violation_data.get('user_id')}")
    
    async def get_warning_count(self, user_id: str, exam_id: str) -> int:
        """Get warning count from Redis"""
        key = f"warning:{user_id}:{exam_id}"
        count = await self.client.get(key)
        return int(count) if count else 0
    
    async def increment_warning(self, user_id: str, exam_id: str):
        """Increment warning count"""
        key = f"warning:{user_id}:{exam_id}"
        await self.client.incr(key)
        await self.client.expire(key, 300)  # 5 minutes

redis_client = RedisClient()