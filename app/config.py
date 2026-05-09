from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    
    # Model paths
    MODEL_PATH: str = "models/yolov8n.pt"
    CUSTOM_MODEL_PATH: Optional[str] = None
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # Detection thresholds
    CONFIDENCE_THRESHOLD: float = 0.35  # Giảm để bắt nhạy hơn
    PERSON_CONFIDENCE_THRESHOLD: float = 0.40
    MULTIPLE_PERSON_CONFIDENCE_THRESHOLD: float = 0.70  # Tăng từ 0.50 lên 0.70 để tránh false positive
    PERSON_MIN_AREA_RATIO: float = 0.015
    IOU_THRESHOLD: float = 0.45
    PHONE_CONFIDENCE_THRESHOLD: float = 0.25  # Threshold riêng cho điện thoại (thấp hơn)
    
    # WebSocket
    MAX_FRAME_SIZE: int = 1024 * 1024  # 1MB
    
    # Proctoring
    MAX_WARNINGS: int = 5
    VIOLATION_WINDOW_SECONDS: int = 60
    VIOLATION_COOLDOWN_SECONDS: int = 2  # Giảm từ 5s xuống 2s
    MULTIPLE_FACES_CONSECUTIVE_FRAMES: int = 3  # Tăng từ 1 lên 3 để tránh false positive
    LEAVING_FRAME_CONSECUTIVE_FRAMES: int = 1  # Giảm từ 2 xuống 1 (báo ngay)
    LOOKING_AWAY_CONSECUTIVE_FRAMES: int = 2
    FACE_OCCLUDED_CONSECUTIVE_FRAMES: int = 2
    EYE_CLOSED_CONSECUTIVE_FRAMES: int = 3
    
    class Config:
        env_file = ".env"

settings = Settings()
