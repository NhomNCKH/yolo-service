# app/models/detector.py
import cv2
import numpy as np
import mediapipe as mp
from typing import List, Dict, Tuple
from ultralytics import YOLO

# Khởi tạo mediapipe solutions
mp_face_mesh = mp.solutions.face_mesh
mp_face_detection = mp.solutions.face_detection

class BehaviorDetector:
    def __init__(self, model: YOLO):
        self.model = model
        self.face_mesh = mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=2,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.face_detection = mp_face_detection.FaceDetection(
            min_detection_confidence=0.5
        )
        
    async def detect_persons(self, frame: np.ndarray) -> List[Dict]:
        """Phát hiện người trong khung hình"""
        # Cần implement method detect trong YOLOModel
        # Tạm thời trả về list rỗng
        return []
    
    async def count_persons(self, frame: np.ndarray) -> int:
        """Đếm số người"""
        persons = await self.detect_persons(frame)
        return len(persons)
    
    async def detect_phones(self, frame: np.ndarray) -> List[Dict]:
        """Phát hiện điện thoại"""
        return []
    
    async def detect_forbidden_objects(self, frame: np.ndarray) -> List[Dict]:
        """Phát hiện vật thể cấm"""
        return []
    
    async def detect_face_orientation(self, frame: np.ndarray) -> Tuple[bool, float]:
        """Phát hiện hướng nhìn"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        
        if not results.multi_face_landmarks:
            return False, 0.0
        
        face_landmarks = results.multi_face_landmarks[0]
        
        # Lấy tọa độ mắt và mũi
        left_eye = face_landmarks.landmark[33]
        right_eye = face_landmarks.landmark[263]
        nose = face_landmarks.landmark[1]
        
        # Tính góc quay đầu (yaw)
        eye_center_x = (left_eye.x + right_eye.x) / 2
        yaw = (eye_center_x - nose.x) * 100
        
        # Nếu góc quay quá lớn (> 30 độ), coi như nhìn đi chỗ khác
        is_looking_away = abs(yaw) > 30
        confidence = min(abs(yaw) / 60, 1.0)
        
        return is_looking_away, confidence
    
    async def detect_face_occlusion(self, frame: np.ndarray) -> Tuple[bool, float]:
        """Phát hiện khuôn mặt bị che"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_detection.process(rgb_frame)
        
        if not results.detections:
            return False, 0.0
        
        # Kiểm tra xem có đủ landmarks không
        detection = results.detections[0]
        if len(detection.location_data.relative_keypoints) < 6:
            return True, 0.7
            
        return False, 0.0
    
    async def detect_leaving_frame(self, frame: np.ndarray, previous_frame_exists: bool = False) -> Tuple[bool, float]:
        """Phát hiện rời khỏi khung hình"""
        persons = await self.detect_persons(frame)
        
        if len(persons) == 0:
            return True, 0.8
        
        return False, 0.0
    
    async def detect_speech(self, frame: np.ndarray) -> Tuple[bool, float]:
        """Phát hiện đang nói chuyện"""
        return False, 0.0
    
    async def detect_eye_closed(self, frame: np.ndarray) -> Tuple[bool, float]:
        """Phát hiện nhắm mắt quá lâu"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        
        if not results.multi_face_landmarks:
            return False, 0.0
        
        face_landmarks = results.multi_face_landmarks[0]
        
        # Lấy tọa độ mắt trái và phải
        left_eye_top = face_landmarks.landmark[159]
        left_eye_bottom = face_landmarks.landmark[145]
        right_eye_top = face_landmarks.landmark[386]
        right_eye_bottom = face_landmarks.landmark[374]
        
        # Tính tỷ lệ mở mắt (EAR - Eye Aspect Ratio)
        left_ear = abs(left_eye_top.y - left_eye_bottom.y)
        right_ear = abs(right_eye_top.y - right_eye_bottom.y)
        avg_ear = (left_ear + right_ear) / 2
        
        # Nếu tỷ lệ quá nhỏ (< 0.2), coi như nhắm mắt
        is_closed = avg_ear < 0.2
        confidence = max(0, 1 - avg_ear / 0.2) if is_closed else 0
        
        return is_closed, confidence