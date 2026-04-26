from __future__ import annotations

from statistics import mean


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _avg(samples: list[dict], key: str, default: float = 0.0) -> float:
    values = [float(item.get(key, default)) for item in samples]
    return mean(values) if values else default


def _event(name: str, severity: float, tip: str) -> dict:
    return {"name": name, "severity": round(_clamp(severity), 3), "tip": tip}


def build_vision_calibration(samples: list[dict]) -> dict:
    face_samples = [item for item in samples if item.get("face_detected")]
    if len(face_samples) < 4:
        return {"ready": False, "reason": "not_enough_face_samples"}

    return {
        "ready": True,
        "eye_contact": _avg(face_samples, "eye_contact", 0.65),
        "posture_score": _avg(face_samples, "posture_score", 0.65),
        "motion_score": _avg(face_samples, "motion_score", 0.12),
        "brow_furrow": _avg(face_samples, "brow_furrow", 0.15),
        "smile_score": _avg(face_samples, "smile_score", 0.2),
        "head_yaw": _avg(face_samples, "head_yaw", 0.0),
        "head_pitch": _avg(face_samples, "head_pitch", 0.0),
        "head_roll": _avg(face_samples, "head_roll", 0.0),
        "face_size": _avg(face_samples, "face_size", 0.22),
        "sample_count": len(face_samples),
    }


def analyze_delivery(
    recent_vision: list[dict],
    calibration: dict | None,
    scenario: str,
) -> dict:
    face_samples = [item for item in recent_vision if item.get("face_detected")]
    face_ratio = len(face_samples) / max(1, len(recent_vision))
    if len(recent_vision) < 4:
        return {"events": [], "confidence": 0.0, "calibrated_scores": {}}

    events: list[dict] = []
    if face_ratio < 0.5:
        return {
            "events": [
                _event("camera_lost", 1.0, "Step back into frame so the audience can read you.")
            ],
            "confidence": round(face_ratio, 3),
            "calibrated_scores": {},
        }

    baseline = calibration if calibration and calibration.get("ready") else {}
    scenario = scenario or "investor_pitch"

    avg_eye = _avg(face_samples, "eye_contact", 0.5)
    avg_posture = _avg(face_samples, "posture_score", 0.5)
    avg_motion = _avg(face_samples, "motion_score", 0.0)
    avg_brow = _avg(face_samples, "brow_furrow", 0.0)
    avg_hand_motion = _avg(face_samples, "hand_motion", 0.0)
    expression_counts: dict[str, int] = {}
    for item in face_samples:
        label = str(item.get("expression", "neutral")).lower()
        expression_counts[label] = expression_counts.get(label, 0) + 1
    dominant_expression = max(expression_counts.items(), key=lambda item: item[1])[0] if expression_counts else "neutral"
    gesture_rate = sum(1 for item in face_samples if item.get("gesture_detected")) / max(1, len(face_samples))
    yaw_delta = abs(_avg(face_samples, "head_yaw", 0.0) - float(baseline.get("head_yaw", 0.0)))
    pitch_delta = _avg(face_samples, "head_pitch", 0.0) - float(baseline.get("head_pitch", 0.0))
    roll_delta = abs(_avg(face_samples, "head_roll", 0.0) - float(baseline.get("head_roll", 0.0)))
    face_size = _avg(face_samples, "face_size", float(baseline.get("face_size", 0.22)))

    eye_base = float(baseline.get("eye_contact", 0.65))
    posture_base = float(baseline.get("posture_score", 0.65))
    motion_base = float(baseline.get("motion_score", 0.12))
    brow_base = float(baseline.get("brow_furrow", 0.15))
    face_size_base = max(0.01, float(baseline.get("face_size", 0.22)))

    eye_threshold = max(0.38, eye_base - 0.25)
    posture_threshold = max(0.45, posture_base - 0.22)
    motion_limit = 0.62 if scenario in {"classroom", "conference"} else 0.52
    gesture_low = 0.04 if scenario in {"job_interview"} else 0.08
    gesture_high = 0.82 if scenario in {"classroom", "conference"} else 0.72

    if avg_eye < eye_threshold and pitch_delta > 0.07:
        events.append(_event("reading_notes", (eye_threshold - avg_eye) + pitch_delta, "Look up from your notes and address the camera."))
    elif avg_eye < eye_threshold:
        events.append(_event("low_eye_contact", eye_threshold - avg_eye, "Bring your eyes back to the camera."))

    if avg_posture < posture_threshold or roll_delta > 0.09:
        severity = max(posture_threshold - avg_posture, roll_delta - 0.09)
        events.append(_event("slouching", severity, "Straighten your shoulders and plant your stance."))

    if gesture_rate < gesture_low and avg_hand_motion < 0.08:
        events.append(_event("stiff_hands", gesture_low - gesture_rate + 0.08 - avg_hand_motion, "Use one deliberate hand gesture on your next point."))
    elif gesture_rate > gesture_high or avg_hand_motion > 0.52:
        severity = max(gesture_rate - gesture_high, avg_hand_motion - 0.52)
        events.append(_event("excessive_gestures", severity, "Quiet your hands and hold still between points."))

    if avg_motion > max(motion_limit, motion_base + 0.28):
        events.append(_event("fidgeting", avg_motion - motion_limit, "Reduce the swaying; reset your feet before continuing."))

    if avg_brow > max(0.52, brow_base + 0.28):
        events.append(_event("tense_expression", avg_brow - max(0.52, brow_base), "Relax your brow so confidence shows on your face."))

    if dominant_expression == "scared":
        events.append(_event("scared_expression", 0.45, "Slow your breath and reset your facial tension."))
    elif dominant_expression == "nervous_smile":
        events.append(_event("nervous_smile", 0.35, "Drop the forced smile and settle into a calm expression."))
    elif dominant_expression == "flat":
        events.append(_event("flat_expression", 0.3, "Add more facial energy to match your message."))

    if yaw_delta > 0.18:
        events.append(_event("looking_away", yaw_delta - 0.18, "Turn your face back toward the audience."))

    if face_size < face_size_base * 0.55 or face_size > face_size_base * 1.65:
        events.append(_event("camera_distance", 0.35, "Adjust your distance so your face and shoulders stay visible."))

    confidence = _clamp(face_ratio * _avg(face_samples, "vision_confidence", 0.75))
    calibrated_scores = {
        "eye_contact": _clamp(avg_eye / max(0.1, eye_base)),
        "posture": _clamp(avg_posture / max(0.1, posture_base)),
        "motion_balance": _clamp(1.0 - max(0.0, avg_motion - motion_base) / 0.6),
        "expression": _clamp(1.0 - max(0.0, avg_brow - brow_base) / 0.55),
    }
    return {
        "events": sorted(events, key=lambda item: item["severity"], reverse=True)[:4],
        "confidence": round(confidence, 3),
        "calibrated_scores": {key: round(value, 3) for key, value in calibrated_scores.items()},
    }
