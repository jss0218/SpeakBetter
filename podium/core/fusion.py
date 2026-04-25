from __future__ import annotations

from statistics import pstdev

from .speech import calculate_filler_score, calculate_pace_score

EYE_CONTACT_WEIGHT = 0.30
FILLER_WEIGHT = 0.25
PACE_WEIGHT = 0.25
ENERGY_VARIANCE_WEIGHT = 0.20

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
    filler_rate: float,
    words_per_minute: float,
    vocal_energy: float,
    pause_count: int,
    elapsed_seconds: float,
    energy_history: list[float],
    engagement_history: list[dict],
) -> tuple[float, str, dict]:
    del pause_count, elapsed_seconds, vocal_energy

    eye_component = _clamp(float(eye_contact_score))
    filler_component = calculate_filler_score(filler_rate)
    pace_component = calculate_pace_score(words_per_minute)
    energy_component = calculate_vocal_energy_variance(energy_history)

    components = {
        "eye_contact": eye_component,
        "fillers": filler_component,
        "pace": pace_component,
        "energy": energy_component,
    }

    score = (
        eye_component * EYE_CONTACT_WEIGHT
        + filler_component * FILLER_WEIGHT
        + pace_component * PACE_WEIGHT
        + energy_component * ENERGY_VARIANCE_WEIGHT
    )
    score = _clamp(score)

    component_values = list(components.values())
    if max(component_values) - min(component_values) <= 0.1:
        dominant_signal = "confident_delivery"
    else:
        dominant_component = max(components.items(), key=lambda kv: abs(kv[1] - 0.5))[0]
        if dominant_component == "eye_contact":
            dominant_signal = "strong_eye_contact" if eye_component >= 0.5 else "poor_eye_contact"
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
    return score, dominant_signal, {k: round(v, 3) for k, v in components.items()}
