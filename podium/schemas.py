from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class VisionUpdateMessage(BaseModel):
    type: Literal["vision_update"]
    eye_contact: float = Field(ge=0.0, le=1.0)
    face_detected: bool
    gesture_detected: bool
    timestamp: float
    posture_score: float = Field(default=0.5, ge=0.0, le=1.0)
    motion_score: float = Field(default=0.0, ge=0.0, le=1.0)
    brow_furrow: float = Field(default=0.0, ge=0.0, le=1.0)
    smile_score: float = Field(default=0.0, ge=0.0, le=1.0)
    expression: str = "neutral"
    head_yaw: float = 0.0
    head_pitch: float = 0.0
    head_roll: float = 0.0
    face_size: float = Field(default=0.0, ge=0.0)
    hand_motion: float = Field(default=0.0, ge=0.0, le=1.0)
    vision_confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class VisionCalibrationMessage(BaseModel):
    type: Literal["vision_calibration"]
    samples: list[dict]
    timestamp: float


class SessionEndMessage(BaseModel):
    type: Literal["session_end"]
    user_id: str


class QAAnswerMessage(BaseModel):
    type: Literal["qa_answer"]
    answer: str
    timestamp: float


class ConnectedMessage(BaseModel):
    type: Literal["connected"]
    session_id: str
    config: dict


class TranscriptMessage(BaseModel):
    type: Literal["transcript"]
    text: str
    filler_count: int
    wpm: float
    pause_detected: bool
    timestamp: float


class EngagementUpdateMessage(BaseModel):
    type: Literal["engagement_update"]
    score: float
    dominant_signal: str
    trend: str
    component_scores: dict


class AudienceUpdateMessage(BaseModel):
    type: Literal["audience_update"]
    avatar_states: dict
    transition_delays_ms: dict


class CoachTipMessage(BaseModel):
    type: Literal["coach_tip"]
    tip: str
    audio_base64: Optional[str] = None


class PressureEventMessage(BaseModel):
    type: Literal["pressure_event"]
    event: str
    payload: dict


class QAQuestionMessage(BaseModel):
    type: Literal["qa_question"]
    question: str
    audio_base64: Optional[str] = None


class SessionBreakdownMessage(BaseModel):
    type: Literal["session_breakdown"]
    breakdown: dict
    engagement_history: list


class ErrorMessage(BaseModel):
    type: Literal["error"]
    message: str
    code: str
