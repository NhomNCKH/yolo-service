import base64
import cv2
import logging
import numpy as np
from datetime import datetime
from typing import Dict, List

from app.config import settings
from app.constants import SUSPICIOUS_ACTIONS, VIOLATION_SEVERITY
from app.models.detector import BehaviorDetector
from app.models.yolo_model import YOLOModel

logger = logging.getLogger(__name__)


TEMPORAL_THRESHOLDS = {
    "leaving_frame": lambda: settings.LEAVING_FRAME_CONSECUTIVE_FRAMES,
    "looking_away": lambda: settings.LOOKING_AWAY_CONSECUTIVE_FRAMES,
    "face_occluded": lambda: settings.FACE_OCCLUDED_CONSECUTIVE_FRAMES,
    "eye_closed": lambda: settings.EYE_CLOSED_CONSECUTIVE_FRAMES,
}


class ProctoringEngine:
    def __init__(self):
        self.model = YOLOModel(settings.MODEL_PATH)
        self.detector = None
        self.user_states: Dict[str, Dict] = {}
        self.is_ready = False

    async def initialize(self):
        if await self.model.load():
            self.detector = BehaviorDetector(self.model)
            self.is_ready = True
            logger.info("Proctoring engine ready")

    async def analyze_frame(self, user_id: str, exam_id: str, image_base64: str) -> Dict:
        if not self.is_ready:
            return {"error": "Model not ready"}

        image_data = base64.b64decode(image_base64)
        np_arr = np.frombuffer(image_data, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None:
            return {"error": "Invalid frame"}

        state = self._get_state(user_id, exam_id)
        violations: List[Dict] = []
        diagnostics = {"person_count": 0, "raw": {}}

        person_count = await self.detector.count_persons(frame)
        diagnostics["person_count"] = person_count

        if person_count > 1:
            violations.append(self._violation(
                "multiple_faces",
                min(person_count * 0.3, 1.0),
                {"person_count": person_count},
            ))

        phones = await self.detector.detect_phones(frame)
        if phones:
            violations.append(self._violation(
                "phone_usage",
                max(p["confidence"] for p in phones),
                {"count": len(phones)},
            ))

        forbidden = await self.detector.detect_forbidden_objects(frame)
        for obj in forbidden:
            violations.append(self._violation(
                "cheating_device",
                obj["confidence"],
                {"object": obj["class"]},
                message=obj["message"],
            ))

        looking_away, look_conf = await self.detector.detect_face_orientation(frame)
        diagnostics["raw"]["looking_away"] = looking_away
        self._add_temporal_violation(
            state,
            violations,
            action="looking_away",
            active=looking_away,
            confidence=look_conf,
        )

        # A visible person should clear any "left frame" streak immediately.
        leaving, leave_conf = await self.detector.detect_leaving_frame(frame)
        if person_count > 0:
            leaving = False
            leave_conf = 0.0
        diagnostics["raw"]["leaving_frame"] = leaving
        self._add_temporal_violation(
            state,
            violations,
            action="leaving_frame",
            active=leaving,
            confidence=leave_conf,
            details={"person_count": person_count},
        )

        occluded, occ_conf = await self.detector.detect_face_occlusion(frame)
        diagnostics["raw"]["face_occluded"] = occluded
        self._add_temporal_violation(
            state,
            violations,
            action="face_occluded",
            active=occluded,
            confidence=occ_conf,
        )

        eyes_closed, eye_conf = await self.detector.detect_eye_closed(frame)
        diagnostics["raw"]["eye_closed"] = eyes_closed
        self._add_temporal_violation(
            state,
            violations,
            action="eye_closed",
            active=eyes_closed,
            confidence=eye_conf,
        )

        counted_violations = self._update_user_state(user_id, exam_id, violations)

        return {
            "user_id": user_id,
            "exam_id": exam_id,
            "violations": counted_violations,
            "warning_count": state["warning_count"],
            "is_blocked": state["is_blocked"],
            "diagnostics": diagnostics,
            "timestamp": datetime.now().isoformat(),
        }

    def _get_state(self, user_id: str, exam_id: str) -> Dict:
        key = f"{user_id}:{exam_id}"
        if key not in self.user_states:
            self.user_states[key] = {
                "violations": [],
                "warning_count": 0,
                "last_violation_time": None,
                "last_action_times": {},
                "streaks": {},
                "is_blocked": False,
            }
        return self.user_states[key]

    def _violation(
        self,
        action: str,
        confidence: float,
        details: Dict | None = None,
        message: str | None = None,
    ) -> Dict:
        return {
            "action": action,
            "message": message or SUSPICIOUS_ACTIONS[action],
            "severity": VIOLATION_SEVERITY[action],
            "confidence": confidence,
            "details": details or {},
        }

    def _add_temporal_violation(
        self,
        state: Dict,
        violations: List[Dict],
        action: str,
        active: bool,
        confidence: float,
        details: Dict | None = None,
    ) -> None:
        streaks = state.setdefault("streaks", {})
        if not active:
            streaks[action] = 0
            return

        streak = int(streaks.get(action, 0)) + 1
        streaks[action] = streak
        threshold = TEMPORAL_THRESHOLDS[action]()

        if streak >= threshold:
            violations.append(self._violation(
                action,
                confidence,
                {**(details or {}), "consecutive_frames": streak, "threshold": threshold},
            ))

    def _update_user_state(self, user_id: str, exam_id: str, violations: List[Dict]) -> List[Dict]:
        state = self._get_state(user_id, exam_id)

        if not violations:
            return []

        current_time = datetime.now()

        if state["last_violation_time"]:
            time_diff = (current_time - state["last_violation_time"]).total_seconds()
            if time_diff > settings.VIOLATION_WINDOW_SECONDS:
                state["warning_count"] = 0

        counted_violations = []
        last_action_times = state.setdefault("last_action_times", {})

        for violation in violations:
            action = violation.get("action", "unknown")
            last_action_time = last_action_times.get(action)
            if last_action_time:
                elapsed = (current_time - last_action_time).total_seconds()
                if elapsed < settings.VIOLATION_COOLDOWN_SECONDS:
                    continue

            state["violations"].append(violation)
            state["warning_count"] += 1
            last_action_times[action] = current_time
            counted_violations.append(violation)

        if counted_violations:
            state["last_violation_time"] = current_time

        if state["warning_count"] >= settings.MAX_WARNINGS:
            state["is_blocked"] = True

        return counted_violations

    async def cleanup(self):
        self.user_states.clear()
        logger.info("Proctoring engine cleaned up")


proctoring_engine = ProctoringEngine()
