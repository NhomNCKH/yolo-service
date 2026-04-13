import asyncio
import cv2
import numpy as np
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from app.models.yolo_model import YOLOModel
from app.models.detector import BehaviorDetector
from app.config import settings
from app.constants import SUSPICIOUS_ACTIONS, VIOLATION_SEVERITY

logger = logging.getLogger(__name__)

class ProctoringEngine:
    def __init__(self):
        self.model = YOLOModel(settings.MODEL_PATH)
        self.detector = None
        self.user_states: Dict[str, Dict] = {}
        self.is_ready = False
        
    async def initialize(self):
        """Initialize model and detector"""
        if await self.model.load():
            self.detector = BehaviorDetector(self.model)
            self.is_ready = True
            logger.info("Proctoring engine ready")
    
    async def analyze_frame(self, user_id: str, exam_id: str, image_base64: str) -> Dict:
        """Analyze single frame for violations"""
        if not self.is_ready:
            return {'error': 'Model not ready'}
        
        # Decode image
        image_data = base64.b64decode(image_base64)
        np_arr = np.frombuffer(image_data, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        violations = []
        
        # 1. Phát hiện nhiều người
        person_count = await self.detector.count_persons(frame)
        if person_count > 1:
            violations.append({
                'action': 'multiple_faces',
                'message': SUSPICIOUS_ACTIONS['multiple_faces'],
                'severity': VIOLATION_SEVERITY['multiple_faces'],
                'confidence': min(person_count * 0.3, 1.0),
                'details': {'person_count': person_count}
            })
        
        # 2. Phát hiện điện thoại
        phones = await self.detector.detect_phones(frame)
        if phones:
            violations.append({
                'action': 'phone_usage',
                'message': SUSPICIOUS_ACTIONS['phone_usage'],
                'severity': VIOLATION_SEVERITY['phone_usage'],
                'confidence': max([p['confidence'] for p in phones]),
                'details': {'count': len(phones)}
            })
        
        # 3. Phát hiện vật thể cấm khác
        forbidden = await self.detector.detect_forbidden_objects(frame)
        for obj in forbidden:
            violations.append({
                'action': 'cheating_device',
                'message': obj['message'],
                'severity': VIOLATION_SEVERITY['cheating_device'],
                'confidence': obj['confidence'],
                'details': {'object': obj['class']}
            })
        
        # 4. Phát hiện hướng nhìn
        looking_away, look_conf = await self.detector.detect_face_orientation(frame)
        if looking_away:
            violations.append({
                'action': 'looking_away',
                'message': SUSPICIOUS_ACTIONS['looking_away'],
                'severity': VIOLATION_SEVERITY['looking_away'],
                'confidence': look_conf,
                'details': {}
            })
        
        # 5. Phát hiện rời khỏi khung hình
        leaving, leave_conf = await self.detector.detect_leaving_frame(frame)
        if leaving:
            violations.append({
                'action': 'leaving_frame',
                'message': SUSPICIOUS_ACTIONS['leaving_frame'],
                'severity': VIOLATION_SEVERITY['leaving_frame'],
                'confidence': leave_conf,
                'details': {}
            })
        
        # 6. Phát hiện che mặt
        occluded, occ_conf = await self.detector.detect_face_occlusion(frame)
        if occluded:
            violations.append({
                'action': 'face_occluded',
                'message': SUSPICIOUS_ACTIONS['face_occluded'],
                'severity': VIOLATION_SEVERITY['face_occluded'],
                'confidence': occ_conf,
                'details': {}
            })
        
        # 7. Phát hiện nhắm mắt
        eyes_closed, eye_conf = await self.detector.detect_eye_closed(frame)
        if eyes_closed:
            violations.append({
                'action': 'eye_closed',
                'message': SUSPICIOUS_ACTIONS['eye_closed'],
                'severity': VIOLATION_SEVERITY['eye_closed'],
                'confidence': eye_conf,
                'details': {}
            })
        
        # Update user state
        user_state = self._update_user_state(user_id, exam_id, violations)
        
        return {
            'user_id': user_id,
            'exam_id': exam_id,
            'violations': violations,
            'warning_count': user_state['warning_count'],
            'is_blocked': user_state['is_blocked'],
            'timestamp': datetime.now().isoformat()
        }
    
    def _update_user_state(self, user_id: str, exam_id: str, violations: List[Dict]) -> Dict:
        """Update user violation state"""
        key = f"{user_id}:{exam_id}"
        
        if key not in self.user_states:
            self.user_states[key] = {
                'violations': [],
                'warning_count': 0,
                'last_violation_time': None,
                'is_blocked': False
            }
        
        state = self.user_states[key]
        
        if violations:
            current_time = datetime.now()
            
            # Check violation window
            if state['last_violation_time']:
                time_diff = (current_time - state['last_violation_time']).total_seconds()
                if time_diff > settings.VIOLATION_WINDOW_SECONDS:
                    state['warning_count'] = 0
            
            # Add violations
            for v in violations:
                state['violations'].append(v)
                state['warning_count'] += 1
            
            state['last_violation_time'] = current_time
            
            # Check block threshold
            if state['warning_count'] >= settings.MAX_WARNINGS:
                state['is_blocked'] = True
        
        return state
    
    async def cleanup(self):
        """Cleanup resources"""
        self.user_states.clear()
        logger.info("Proctoring engine cleaned up")

proctoring_engine = ProctoringEngine()