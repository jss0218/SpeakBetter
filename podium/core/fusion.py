from __future__ import annotations

from statistics import pstdev

from .speech import calculate_filler_score, calculate_pace_score

EYE_CONTACT_WEIGHT = 0.28
POSTURE_WEIGHT = 0.14
GESTURE_WEIGHT = 0.12
MOTION_WEIGHT = 0.10
EXPRESSION_WEIGHT = 0.08
FILLER_WEIGHT = 0.12
PACE_WEIGHT = 0.10
ENERGY_VARIANCE_WEIGHT = 0.06

DOMINANT_SIGNAL_OPTIONS = [
    "strong_eye_contact",
    "poor_eye_contact",
    "good_pace",
    "too_fast",
    "too_slow",
    "low_fillers",
    "high_filler_rate",
    "good_energy",
    "monotone",
    "strong_posture",
    "poor_posture",
    "good_gestures",
    "stiff_delivery",
    "fidgeting",
    "composed_motion",
    "tense_expression",
    "confident_delivery",
    "nervous_delivery",
]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def calculate_vocal_energy_variance(energy_history: list[float]) -> float:
    if len(energy_history) < 5:
        return 0.5

    std = pstdev([_clamp(float(v)) for v in energy_history])
    if std < 0.05:
        return 0.2
    if std <= 0.15:
        return 1.0
    if std <= 0.25:
        return 0.7
    return 0.4


def calculate_motion_balance(motion_score: float) -> float:
    motion = _clamp(float(motion_score))
    if motion < 0.05:
        return 0.65
    if motion <= 0.35:
        return 1.0
    if motion <= 0.55:
        return 0.7
    return 0.35


def calculate_expression_score(brow_furrow: float, smile_score: float, expression: str) -> float:
    brow = _clamp(float(brow_furrow))
    smile = _clamp(float(smile_score))
    label = (expression or "").lower()

    if "happy" in label or "focused" in label or "engaged" in label:
        return 0.9
    if "nervous" in label:
        return 0.55
    if "concerned" in label:
        return 0.5
    if "scared" in label:
        return 0.3
    if "surprised" in label:
        return 0.6
    if "flat" in label:
        return 0.45
    if "tense" in label or brow > 0.55:
        return 0.35
    if smile > 0.85:
        return 0.65
    if "smiling" in label or smile >= 0.25:
        return 0.9
    return 0.75


def calculate_trend(engagement_history: list[dict]) -> str:
    if len(engagement_history) < 6:
        return "stable"

    last_six = engagement_history[-6:]
    first_avg = sum(entry.get("score", 0.0) for entry in last_six[:3]) / 3.0
    second_avg = sum(entry.get("score", 0.0) for entry in last_six[3:]) / 3.0
    delta = second_avg - first_avg

    if delta > 0.08:
        return "rising"
    if delta < -0.08:
        return "falling"
    return "stable"


def calculate_engagement(
    eye_contact_score: float,
    posture_score: float = 0.5,
    gesture_score: float = 0.4,
    motion_score: float = 0.0,
    brow_furrow: float = 0.0,
    smile_score: float = 0.0,
    expression: str = "neutral",
    filler_rate: float = 0.0,
    words_per_minute: float = 0.0,
    vocal_energy: float = 0.0,
    pause_count: int = 0,
    elapsed_seconds: float = 0.0,
    energy_history: list[float] | None = None,
    engagement_history: list[dict] | None = None,
    delivery_events: list[dict] | None = None,
    vision_confidence: float = 1.0,
) -> tuple[float, str, dict]:
    del pause_count, elapsed_seconds, vocal_energy
    energy_history = energy_history or []
    engagement_history = engagement_history or []
    delivery_events = delivery_events or []
    vision_confidence = _clamp(float(vision_confidence), 0.25, 1.0)

    eye_component = _clamp(float(eye_contact_score))
    posture_component = _clamp(float(posture_score))
    gesture_component = _clamp(float(gesture_score))
    motion_component = calculate_motion_balance(motion_score)
    expression_component = calculate_expression_score(brow_furrow, smile_score, expression)
    filler_component = calculate_filler_score(filler_rate)
    pace_component = calculate_pace_score(words_per_minute)
    energy_component = calculate_vocal_energy_variance(energy_history)

    components = {
        "eye_contact": eye_component,
        "posture": posture_component,
        "gestures": gesture_component,
        "motion_balance": motion_component,
        "expression": expression_component,
        "fillers": filler_component,
        "pace": pace_component,
        "energy": energy_component,
    }

    score = (
        eye_component * EYE_CONTACT_WEIGHT
        + posture_component * POSTURE_WEIGHT
        + gesture_component * GESTURE_WEIGHT
        + motion_component * MOTION_WEIGHT
        + expression_component * EXPRESSION_WEIGHT
        + filler_component * FILLER_WEIGHT
        + pace_component * PACE_WEIGHT
        + energy_component * ENERGY_VARIANCE_WEIGHT
    )
    event_penalty = sum(float(event.get("severity", 0.0)) for event in delivery_events[:3]) * 0.12
    score -= event_penalty * vision_confidence
    score = _clamp(score)

    component_values = list(components.values())
    if delivery_events and vision_confidence >= 0.4:
        event_name = str(delivery_events[0].get("name", ""))
        dominant_signal = {
            "reading_notes": "poor_eye_contact",
            "low_eye_contact": "poor_eye_contact",
            "slouching": "poor_posture",
            "stiff_hands": "stiff_delivery",
            "excessive_gestures": "fidgeting",
            "fidgeting": "fidgeting",
            "tense_expression": "tense_expression",
            "looking_away": "poor_eye_contact",
            "camera_lost": "poor_eye_contact",
            "camera_distance": "nervous_delivery",
            "scared_expression": "tense_expression",
            "nervous_smile": "tense_expression",
            "flat_expression": "tense_expression",
        }.get(event_name, "nervous_delivery")
    elif max(component_values) - min(component_values) <= 0.1:
        dominant_signal = "confident_delivery"
    else:
        weak_components = {name: value for name, value in components.items() if value < 0.5}
        if weak_components:
            dominant_component = min(weak_components.items(), key=lambda kv: kv[1])[0]
        else:
            dominant_component = max(components.items(), key=lambda kv: kv[1])[0]
        if dominant_component == "eye_contact":
            dominant_signal = "strong_eye_contact" if eye_component >= 0.5 else "poor_eye_contact"
        elif dominant_component == "posture":
            dominant_signal = "strong_posture" if posture_component >= 0.5 else "poor_posture"
        elif dominant_component == "gestures":
            dominant_signal = "good_gestures" if gesture_component >= 0.5 else "stiff_delivery"
        elif dominant_component == "motion_balance":
            dominant_signal = "composed_motion" if motion_component >= 0.5 else "fidgeting"
        elif dominant_component == "expression":
            dominant_signal = "confident_delivery" if expression_component >= 0.5 else "tense_expression"
        elif dominant_component == "fillers":
            dominant_signal = "low_fillers" if filler_component >= 0.5 else "high_filler_rate"
        elif dominant_component == "pace":
            if pace_component >= 0.5:
                dominant_signal = "good_pace"
            else:
                dominant_signal = "too_fast" if words_per_minute > 150 else "too_slow"
        else:
            dominant_signal = "good_energy" if energy_component >= 0.5 else "monotone"

    trend = calculate_trend(engagement_history + [{"score": score}])
    components["vision_confidence"] = vision_confidence
    components["delivery_penalty"] = _clamp(event_penalty)
    return score, dominant_signal, {k: round(v, 3) for k, v in components.items()}
