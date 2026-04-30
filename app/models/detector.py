# app/models/detector.py
import cv2
import mediapipe as mp
import numpy as np
from typing import Dict, List, Tuple
from ultralytics import YOLO

from app.config import settings

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
            min_tracking_confidence=0.5,
        )
        self.face_detection = mp_face_detection.FaceDetection(
            min_detection_confidence=0.5,
        )

    async def detect_persons(self, frame: np.ndarray) -> List[Dict]:
        """Detect people in the camera frame.

        YOLO is the primary detector. MediaPipe face detection is a fallback
        because webcam frames can occasionally miss a full body/person box while
        the candidate's face is still clearly visible.
        """
        detections = await self.model.detect(
            frame,
            conf_threshold=settings.PERSON_CONFIDENCE_THRESHOLD,
        )
        persons = [d for d in detections if d.get("class") == "person"]

        if persons:
            return persons

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_results = self.face_detection.process(rgb_frame)
        fallback_persons: List[Dict] = []

        for detection in face_results.detections or []:
            score = float(detection.score[0]) if detection.score else 0.0
            if score < 0.45:
                continue

            box = detection.location_data.relative_bounding_box
            height, width = frame.shape[:2]
            x1 = max(0, int(box.xmin * width))
            y1 = max(0, int(box.ymin * height))
            x2 = min(width, int((box.xmin + box.width) * width))
            y2 = min(height, int((box.ymin + box.height) * height))
            fallback_persons.append({
                "class": "person",
                "class_id": 0,
                "confidence": score,
                "bbox": [x1, y1, x2, y2],
                "source": "face_fallback",
            })

        return fallback_persons

    async def count_persons(self, frame: np.ndarray) -> int:
        persons = await self.detect_persons(frame)
        return len(persons)

    async def detect_phones(self, frame: np.ndarray) -> List[Dict]:
        return await self.model.detect_objects(frame, ["cell phone"])

    async def detect_forbidden_objects(self, frame: np.ndarray) -> List[Dict]:
        objects = await self.model.detect_objects(frame, ["laptop", "book", "remote"])
        return [
            {
                **obj,
                "message": f"Detected forbidden object: {obj['class']}",
            }
            for obj in objects
            if obj.get("confidence", 0) >= settings.CONFIDENCE_THRESHOLD
        ]

    async def detect_face_orientation(self, frame: np.ndarray) -> Tuple[bool, float]:
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)

        if not results.multi_face_landmarks:
            return False, 0.0

        face_landmarks = results.multi_face_landmarks[0]
        left_eye = face_landmarks.landmark[33]
        right_eye = face_landmarks.landmark[263]
        nose = face_landmarks.landmark[1]

        eye_center_x = (left_eye.x + right_eye.x) / 2
        yaw = (eye_center_x - nose.x) * 100

        is_looking_away = abs(yaw) > 30
        confidence = min(abs(yaw) / 60, 1.0)

        return is_looking_away, confidence

    async def detect_face_occlusion(self, frame: np.ndarray) -> Tuple[bool, float]:
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_detection.process(rgb_frame)

        if not results.detections:
            return False, 0.0

        detection = results.detections[0]
        if len(detection.location_data.relative_keypoints) < 6:
            return True, 0.7

        return False, 0.0

    async def detect_leaving_frame(
        self,
        frame: np.ndarray,
        previous_frame_exists: bool = False,
    ) -> Tuple[bool, float]:
        persons = await self.detect_persons(frame)

        if len(persons) == 0:
            return True, 0.8

        return False, 0.0

    async def detect_speech(self, frame: np.ndarray) -> Tuple[bool, float]:
        return False, 0.0

    async def detect_eye_closed(self, frame: np.ndarray) -> Tuple[bool, float]:
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)

        if not results.multi_face_landmarks:
            return False, 0.0

        landmarks = results.multi_face_landmarks[0].landmark

        def eye_ratio(outer_idx: int, inner_idx: int, top_idx: int, bottom_idx: int) -> float:
            outer = landmarks[outer_idx]
            inner = landmarks[inner_idx]
            top = landmarks[top_idx]
            bottom = landmarks[bottom_idx]
            eye_width = max(abs(outer.x - inner.x), 1e-6)
            eye_height = abs(top.y - bottom.y)
            return eye_height / eye_width

        left_ratio = eye_ratio(33, 133, 159, 145)
        right_ratio = eye_ratio(362, 263, 386, 374)
        avg_ratio = (left_ratio + right_ratio) / 2

        is_closed = avg_ratio < 0.18
        confidence = max(0.0, min((0.18 - avg_ratio) / 0.18, 1.0)) if is_closed else 0.0

        return is_closed, confidence
