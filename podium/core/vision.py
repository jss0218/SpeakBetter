from __future__ import annotations


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def update_eye_contact_ema(current_ema: float, new_value: float, alpha: float = 0.3) -> float:
    alpha = _clamp(alpha, 0.0, 1.0)
    ema = (1.0 - alpha) * _clamp(current_ema) + alpha * _clamp(new_value)
    return _clamp(ema)


def calculate_gesture_score(gesture_history: list[bool]) -> float:
    if not gesture_history:
        return 0.4

    recent = gesture_history[-60:]
    gestures = sum(1 for g in recent if g)
    gesture_rate = gestures / max(1, len(recent))

    if gesture_rate == 0:
        return 0.4
    if 0.08 <= gesture_rate <= 0.45:
        return 1.0
    if 0.45 < gesture_rate <= 0.65:
        return 0.7
    return 0.4
