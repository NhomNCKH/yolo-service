# app/models/yolo_model.py
import cv2
import numpy as np
from ultralytics import YOLO
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class YOLOModel:
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.model = None
        self.classes = {}
        
    async def load(self):
        """Load YOLO model"""
        try:
            self.model = YOLO(self.model_path)
            self.classes = self.model.names
            logger.info(f"YOLO model loaded from {self.model_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False
    
    async def detect(self, frame: np.ndarray, conf_threshold: float = 0.5) -> List[Dict[str, Any]]:
        """Run detection on frame"""
        if self.model is None:
            raise ValueError("Model not loaded")
        
        results = self.model(frame, conf=conf_threshold, verbose=False)
        
        detections = []
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    conf = float(box.conf[0])
                    cls = int(box.cls[0])
                    class_name = self.classes[cls]
                    
                    detections.append({
                        'class': class_name,
                        'class_id': cls,
                        'confidence': conf,
                        'bbox': [int(x1), int(y1), int(x2), int(y2)]
                    })
        
        return detections
    
    async def detect_objects(self, frame: np.ndarray, target_classes: List[str]) -> List[Dict]:
        """Detect specific classes only"""
        all_detections = await self.detect(frame)
        return [d for d in all_detections if d['class'] in target_classes]