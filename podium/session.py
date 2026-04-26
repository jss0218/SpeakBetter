from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import random
import threading
from typing import Optional
from uuid import uuid4

SCENARIOS = {"pitch", "interview", "presentation"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class SessionState:
    session_id: str
    user_id: str
    scenario: str
    target_duration: int
    started_at: datetime
    ended_at: Optional[datetime] = None

    transcript: list[dict] = field(default_factory=list)
    full_transcript: str = ""
    filler_count: int = 0
    filler_rate: float = 0.0
    words_per_minute: float = 0.0
    word_count: int = 0
    pause_detected: bool = False
    pause_count: int = 0
    vocal_energy: float = 0.0
    energy_history: list[float] = field(default_factory=list)

    eye_contact_score: float = 0.5
    face_detected: bool = False
    gesture_detected: bool = False
    gesture_history: list[bool] = field(default_factory=list)
    gesture_score: float = 0.4
    posture_score: float = 0.5
    motion_score: float = 0.0
    expression: str = "neutral"
    brow_furrow: float = 0.0
    smile_score: float = 0.0
    vision_history: list[dict] = field(default_factory=list)
    vision_calibration: dict = field(default_factory=dict)
    vision_confidence: float = 0.0
    delivery_events: list[dict] = field(default_factory=list)
    calibrated_vision_scores: dict = field(default_factory=dict)

    engagement_score: float = 0.5
    engagement_history: list[dict] = field(default_factory=list)
    dominant_signal: str = "confident_delivery"
    engagement_trend: str = "stable"
    high_engagement_streak: int = 0

    avatar_states: dict[str, str] = field(default_factory=dict)
    avatar_stubbornness: dict[str, float] = field(default_factory=dict)
    audience_size: int = 8

    pressure_level: int = 1
    pressure_events_fired: list[str] = field(default_factory=list)

    claims: list[str] = field(default_factory=list)
    weakest_claim: str = ""
    gap_explanation: str = ""
    adversarial_question: str = ""
    user_qa_answer: str = ""
    session_phase: str = "speaking"
    qa_answer_transcript: str = ""
    qa_question_count: int = 0

    coach_tips: list[dict] = field(default_factory=list)
    last_tip_timestamp: float = 0.0
    last_vision_tip_signal: str = ""
    final_breakdown: Optional[dict] = None

    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False, compare=False)

    @classmethod
    def from_config(
        cls,
        user_id: str,
        scenario: str,
        target_duration: int,
        audience_size: int = 8,
    ) -> "SessionState":
        if scenario not in SCENARIOS:
            raise ValueError(f"Unsupported scenario: {scenario}")
        if target_duration <= 0:
            raise ValueError("target_duration must be positive")

        audience_size = max(1, min(20, int(audience_size)))
        avatar_states: dict[str, str] = {}
        avatar_stubbornness: dict[str, float] = {}

        for i in range(audience_size):
            avatar_id = f"avatar_{i}"
            avatar_states[avatar_id] = "neutral"
            if random.random() < 0.2:
                avatar_stubbornness[avatar_id] = round(random.uniform(0.7, 0.9), 3)
            else:
                avatar_stubbornness[avatar_id] = round(random.uniform(0.1, 0.4), 3)

        return cls(
            session_id=str(uuid4()),
            user_id=user_id,
            scenario=scenario,
            target_duration=target_duration,
            started_at=_utc_now(),
            avatar_states=avatar_states,
            avatar_stubbornness=avatar_stubbornness,
            audience_size=audience_size,
        )

    def update_engagement(self, score: float, signal: str, trend: str) -> None:
        now = self.get_elapsed_seconds()
        score = max(0.0, min(1.0, float(score)))
        with self._lock:
            self.engagement_score = score
            self.dominant_signal = signal
            self.engagement_trend = trend
            self.engagement_history.append(
                {
                    "score": score,
                    "timestamp": now,
                    "dominant_signal": signal,
                }
            )
            if score > 0.75:
                if len(self.engagement_history) > 1:
                    prev_t = self.engagement_history[-2]["timestamp"]
                    self.high_engagement_streak += int(max(1.0, now - prev_t))
                else:
                    self.high_engagement_streak += 2
            else:
                self.high_engagement_streak = 0

    def add_transcript_chunk(self, text: str, fillers: int, wpm: float, energy: float) -> None:
        clean_text = (text or "").strip()
        if not clean_text:
            return

        now = self.get_elapsed_seconds()
        words = clean_text.split()

        with self._lock:
            self.word_count += len(words)
            self.filler_count += max(0, int(fillers))
            elapsed_minutes = max(now / 60.0, 1 / 60.0)
            self.filler_rate = float(self.filler_count) / elapsed_minutes
            self.words_per_minute = max(0.0, float(wpm))
            self.vocal_energy = max(0.0, min(1.0, float(energy)))
            self.full_transcript = (self.full_transcript + " " + clean_text).strip()
            self.transcript.append(
                {
                    "text": clean_text,
                    "timestamp": now,
                    "cumulative_fillers": self.filler_count,
                }
            )
            self.energy_history.append(self.vocal_energy)
            if len(self.energy_history) > 30:
                self.energy_history = self.energy_history[-30:]
            if self.session_phase == "qa_answering":
                self.qa_answer_transcript = (self.qa_answer_transcript + " " + clean_text).strip()

    def update_vision(
        self,
        eye_contact: float,
        face_detected: bool,
        gesture: bool,
        posture_score: float = 0.5,
        motion_score: float = 0.0,
        brow_furrow: float = 0.0,
        smile_score: float = 0.0,
        expression: str = "neutral",
        head_yaw: float = 0.0,
        head_pitch: float = 0.0,
        head_roll: float = 0.0,
        face_size: float = 0.0,
        hand_motion: float = 0.0,
        vision_confidence: float = 0.5,
    ) -> None:
        from podium.core.delivery import analyze_delivery
        from podium.core.vision import calculate_gesture_score

        now = self.get_elapsed_seconds()
        eye_contact = max(0.0, min(1.0, float(eye_contact)))
        posture_score = max(0.0, min(1.0, float(posture_score)))
        motion_score = max(0.0, min(1.0, float(motion_score)))
        brow_furrow = max(0.0, min(1.0, float(brow_furrow)))
        smile_score = max(0.0, min(1.0, float(smile_score)))
        hand_motion = max(0.0, min(1.0, float(hand_motion)))
        vision_confidence = max(0.0, min(1.0, float(vision_confidence)))
        face_size = max(0.0, float(face_size))
        expression = (expression or "neutral").strip().lower()[:40]
        with self._lock:
            self.eye_contact_score = 0.3 * eye_contact + 0.7 * self.eye_contact_score
            self.face_detected = bool(face_detected)
            self.gesture_detected = bool(gesture)
            self.gesture_history.append(bool(gesture))
            if len(self.gesture_history) > 60:
                self.gesture_history = self.gesture_history[-60:]
            self.gesture_score = calculate_gesture_score(self.gesture_history)
            self.posture_score = 0.35 * posture_score + 0.65 * self.posture_score
            self.motion_score = 0.35 * motion_score + 0.65 * self.motion_score
            self.brow_furrow = 0.35 * brow_furrow + 0.65 * self.brow_furrow
            self.smile_score = 0.35 * smile_score + 0.65 * self.smile_score
            self.vision_confidence = 0.35 * vision_confidence + 0.65 * self.vision_confidence
            self.expression = expression
            self.vision_history.append(
                {
                    "timestamp": now,
                    "eye_contact": eye_contact,
                    "face_detected": bool(face_detected),
                    "gesture_detected": bool(gesture),
                    "posture_score": posture_score,
                    "motion_score": motion_score,
                    "brow_furrow": brow_furrow,
                    "smile_score": smile_score,
                    "expression": expression,
                    "head_yaw": float(head_yaw),
                    "head_pitch": float(head_pitch),
                    "head_roll": float(head_roll),
                    "face_size": face_size,
                    "hand_motion": hand_motion,
                    "vision_confidence": vision_confidence,
                }
            )
            if len(self.vision_history) > 240:
                self.vision_history = self.vision_history[-240:]
            delivery = analyze_delivery(
                recent_vision=[
                    entry for entry in self.vision_history if entry["timestamp"] >= now - 10
                ],
                calibration=self.vision_calibration,
                scenario=self.scenario,
            )
            self.delivery_events = list(delivery.get("events", []))
            self.calibrated_vision_scores = dict(delivery.get("calibrated_scores", {}))
            self.vision_confidence = float(delivery.get("confidence", self.vision_confidence))

    def update_vision_calibration(self, samples: list[dict]) -> None:
        from podium.core.delivery import build_vision_calibration

        calibration = build_vision_calibration(samples)
        with self._lock:
            if calibration.get("ready"):
                self.vision_calibration = calibration

    def get_recent_vision(self, seconds: int = 10) -> list[dict]:
        with self._lock:
            cutoff = self.get_elapsed_seconds() - max(1, seconds)
            return [entry.copy() for entry in self.vision_history if entry["timestamp"] >= cutoff]

    def fire_pressure_event(self, event_name: str) -> None:
        with self._lock:
            self.pressure_events_fired.append(event_name)
            if event_name in {"audience_size_increase", "distraction_inject"}:
                self.pressure_level = max(self.pressure_level, 2)
            elif event_name in {"timer_appear", "hand_raise"}:
                self.pressure_level = max(self.pressure_level, 3)

    def get_snapshot(self) -> dict:
        with self._lock:
            return {
                "engagement_score": self.engagement_score,
                "dominant_signal": self.dominant_signal,
                "avatar_states": dict(self.avatar_states),
                "audience_size": self.audience_size,
                "filler_count": self.filler_count,
                "wpm": self.words_per_minute,
                "eye_contact_score": self.eye_contact_score,
                "posture_score": self.posture_score,
                "gesture_score": self.gesture_score,
                "motion_score": self.motion_score,
                "expression": self.expression,
                "vision_confidence": self.vision_confidence,
                "delivery_events": list(self.delivery_events),
                "calibrated_vision_scores": dict(self.calibrated_vision_scores),
                "session_phase": self.session_phase,
            }

    def get_elapsed_seconds(self) -> float:
        end_time = self.ended_at or _utc_now()
        return max(0.0, (end_time - self.started_at).total_seconds())

    def get_recent_transcript(self, seconds: int = 30) -> str:
        with self._lock:
            cutoff = self.get_elapsed_seconds() - max(1, seconds)
            chunks = [entry["text"] for entry in self.transcript if entry["timestamp"] >= cutoff]
        return " ".join(chunks).strip()

    def to_mongo(self) -> dict:
        with self._lock:
            return {
                "session_id": self.session_id,
                "user_id": self.user_id,
                "scenario": self.scenario,
                "target_duration": self.target_duration,
                "started_at": self.started_at.isoformat(),
                "ended_at": self.ended_at.isoformat() if self.ended_at else None,
                "transcript": list(self.transcript),
                "full_transcript": self.full_transcript,
                "filler_count": self.filler_count,
                "filler_rate": self.filler_rate,
                "words_per_minute": self.words_per_minute,
                "word_count": self.word_count,
                "pause_detected": self.pause_detected,
                "pause_count": self.pause_count,
                "vocal_energy": self.vocal_energy,
                "energy_history": list(self.energy_history),
                "eye_contact_score": self.eye_contact_score,
                "face_detected": self.face_detected,
                "gesture_detected": self.gesture_detected,
                "gesture_history": list(self.gesture_history),
                "gesture_score": self.gesture_score,
                "posture_score": self.posture_score,
                "motion_score": self.motion_score,
                "expression": self.expression,
                "brow_furrow": self.brow_furrow,
                "smile_score": self.smile_score,
                "vision_history": list(self.vision_history),
                "vision_calibration": dict(self.vision_calibration),
                "vision_confidence": self.vision_confidence,
                "delivery_events": list(self.delivery_events),
                "calibrated_vision_scores": dict(self.calibrated_vision_scores),
                "engagement_score": self.engagement_score,
                "engagement_history": list(self.engagement_history),
                "dominant_signal": self.dominant_signal,
                "engagement_trend": self.engagement_trend,
                "high_engagement_streak": self.high_engagement_streak,
                "avatar_states": dict(self.avatar_states),
                "avatar_stubbornness": dict(self.avatar_stubbornness),
                "audience_size": self.audience_size,
                "pressure_level": self.pressure_level,
                "pressure_events_fired": list(self.pressure_events_fired),
                "claims": list(self.claims),
                "weakest_claim": self.weakest_claim,
                "gap_explanation": self.gap_explanation,
                "adversarial_question": self.adversarial_question,
                "user_qa_answer": self.user_qa_answer,
                "session_phase": self.session_phase,
                "qa_answer_transcript": self.qa_answer_transcript,
                "qa_question_count": self.qa_question_count,
                "coach_tips": list(self.coach_tips),
                "last_tip_timestamp": self.last_tip_timestamp,
                "last_vision_tip_signal": self.last_vision_tip_signal,
                "final_breakdown": self.final_breakdown,
            }
