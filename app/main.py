import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.services.websocket_manager import manager
from app.services.proctoring_engine import proctoring_engine
from app.services.redis_client import redis_client
from app.api import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi tạo
    logger.info("Starting YOLO Proctoring Service...")
    await proctoring_engine.initialize()
    try:
        await redis_client.connect()
    except Exception as exc:
        logger.warning(f"Redis unavailable during startup: {exc}")
    yield
    # Dọn dẹp
    await redis_client.close()
    await proctoring_engine.cleanup()
    logger.info("Shutting down...")

app = FastAPI(
    title="YOLO Proctoring Service",
    description="Real-time exam proctoring using YOLO",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api")

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "model_loaded": proctoring_engine.is_ready,
        "redis_connected": await redis_client.ping(),
    }

@app.websocket("/ws/{user_id}/{exam_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, exam_id: str):
    await manager.connect(websocket, user_id, exam_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            await manager.handle_frame(user_id, exam_id, data)
            
    except WebSocketDisconnect:
        manager.disconnect(user_id, exam_id)
