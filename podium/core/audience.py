from __future__ import annotations

import random

AVATAR_STATES = ["engaged", "neutral", "bored", "confused", "distracted"]


BASE_DISTRIBUTIONS = {
    "high": {"engaged": 0.60, "neutral": 0.25, "bored": 0.10, "confused": 0.03, "distracted": 0.02},
    "mid_high": {"engaged": 0.30, "neutral": 0.40, "bored": 0.20, "confused": 0.07, "distracted": 0.03},
    "mid_low": {"engaged": 0.15, "neutral": 0.25, "bored": 0.40, "confused": 0.12, "distracted": 0.08},
    "low": {"engaged": 0.05, "neutral": 0.10, "bored": 0.45, "confused": 0.25, "distracted": 0.15},
}

MODIFIERS = {
    "high_filler_rate": {"confused": 0.15, "engaged": -0.10},
    "too_fast": {"confused": 0.20, "engaged": -0.15},
    "too_slow": {"bored": 0.20, "engaged": -0.10},
    "poor_eye_contact": {"distracted": 0.15, "engaged": -0.10},
    "monotone": {"bored": 0.25, "engaged": -0.15},
}


def _renormalize(dist: dict[str, float]) -> dict[str, float]:
    clean = {k: max(0.0, float(v)) for k, v in dist.items()}
    total = sum(clean.values())
    if total <= 0:
        return {state: 1.0 / len(AVATAR_STATES) for state in AVATAR_STATES}
    return {k: v / total for k, v in clean.items()}


def _sample_distribution(distribution: dict[str, float]) -> str:
    rand = random.random()
    cumulative = 0.0
    for state, prob in distribution.items():
        cumulative += prob
        if rand <= cumulative:
            return state
    return "neutral"


def _base_distribution(engagement_score: float) -> dict[str, float]:
    score = max(0.0, min(1.0, float(engagement_score)))
    if score > 0.75:
        return dict(BASE_DISTRIBUTIONS["high"])
    if score >= 0.55:
        return dict(BASE_DISTRIBUTIONS["mid_high"])
    if score >= 0.35:
        return dict(BASE_DISTRIBUTIONS["mid_low"])
    return dict(BASE_DISTRIBUTIONS["low"])


def initialize_avatars(audience_size: int) -> tuple[dict, dict]:
    audience_size = max(0, int(audience_size))
    states: dict[str, str] = {}
    stubbornness: dict[str, float] = {}

    for idx in range(audience_size):
        avatar_id = f"avatar_{idx}"
        states[avatar_id] = "neutral"
        if random.random() < 0.2:
            stubbornness[avatar_id] = round(random.uniform(0.7, 0.9), 3)
        else:
            stubbornness[avatar_id] = round(random.uniform(0.1, 0.4), 3)

    return states, stubbornness


def calculate_avatar_states(
    engagement_score: float,
    dominant_signal: str,
    current_states: dict[str, str],
    stubbornness_factors: dict[str, float],
    audience_size: int,
) -> tuple[dict[str, str], dict[str, int]]:
    states = dict(current_states)
    delays: dict[str, int] = {}

    for idx in range(audience_size):
        avatar_id = f"avatar_{idx}"
        states.setdefault(avatar_id, "neutral")
        stubbornness_factors.setdefault(
            avatar_id,
            round(random.uniform(0.7, 0.9), 3) if random.random() < 0.2 else round(random.uniform(0.1, 0.4), 3),
        )

    distribution = _base_distribution(engagement_score)
    if dominant_signal in MODIFIERS:
        for state, delta in MODIFIERS[dominant_signal].items():
            distribution[state] = distribution.get(state, 0.0) + delta
        distribution = _renormalize(distribution)

    for avatar_id, current in list(states.items()):
        if avatar_id not in stubbornness_factors:
            continue
        change_probability = 1.0 - max(0.0, min(1.0, stubbornness_factors[avatar_id]))
        if random.random() > change_probability:
            continue

        if random.random() < 0.10:
            new_state = random.choice(AVATAR_STATES)
        else:
            new_state = _sample_distribution(distribution)

        if new_state != current:
            states[avatar_id] = new_state
            delays[avatar_id] = random.randint(0, 800)

    return states, delays


def expand_audience(
    current_states: dict,
    stubbornness_factors: dict,
    new_size: int,
    current_engagement: float,
) -> tuple[dict, dict]:
    states = dict(current_states)
    stubbornness = dict(stubbornness_factors)

    start_size = len(states)
    if new_size <= start_size:
        return states, stubbornness

    current_dist = _base_distribution(current_engagement)
    for avatar_idx in range(start_size, new_size):
        avatar_id = f"avatar_{avatar_idx}"
        if random.random() < 0.5:
            states[avatar_id] = "neutral"
        else:
            states[avatar_id] = _sample_distribution(current_dist)

        if random.random() < 0.2:
            stubbornness[avatar_id] = round(random.uniform(0.7, 0.9), 3)
        else:
            stubbornness[avatar_id] = round(random.uniform(0.1, 0.4), 3)

    return states, stubbornness
