from fastapi import APIRouter, UploadFile, File, Form
from typing import Optional
import base64
import cv2
import numpy as np

from app.services.proctoring_engine import proctoring_engine

router = APIRouter()

@router.post("/analyze")
async def analyze_image(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    exam_id: str = Form(...)
):
    """Analyze uploaded image"""
    contents = await file.read()
    image_base64 = base64.b64encode(contents).decode('utf-8')
    
    result = await proctoring_engine.analyze_frame(
        user_id, exam_id, image_base64
    )
    
    return result

@router.get("/status")
async def get_status():
    """Get service status"""
    return {
        "status": "running",
        "model_ready": proctoring_engine.is_ready
    }