from __future__ import annotations

import random


def get_initial_audience_size() -> int:
    return 8


def check_pressure_events(
    pressure_events_fired: list[str],
    high_engagement_streak: float,
    elapsed_seconds: float,
    target_duration: int,
    audience_size: int,
    avatar_states: dict,
    last_distraction_time: float,
) -> list[dict]:
    events: list[dict] = []
    fired = pressure_events_fired or []
    initial_size = get_initial_audience_size()

    if (
        high_engagement_streak >= 30
        and "audience_size_increase" not in fired
        and audience_size == initial_size
    ):
        events.append(
            {
                "event": "audience_size_increase",
                "payload": {"from": audience_size, "to": audience_size * 5},
            }
        )

    if high_engagement_streak >= 60 and "timer_appear" not in fired:
        events.append({"event": "timer_appear", "payload": {"seconds": 90}})

    if (
        target_duration > 0
        and elapsed_seconds >= target_duration * 0.60
        and "hand_raise" not in fired
        and avatar_states
    ):
        events.append(
            {
                "event": "hand_raise",
                "payload": {"avatar_id": random.choice(list(avatar_states.keys()))},
            }
        )

    last_gap_ok = last_distraction_time <= 0 or (elapsed_seconds - last_distraction_time) > 60
    if (
        high_engagement_streak >= 45
        and fired.count("distraction_inject") < 2
        and last_gap_ok
        and len(avatar_states) >= 2
    ):
        events.append(
            {
                "event": "distraction_inject",
                "payload": {
                    "avatar_ids": random.sample(list(avatar_states.keys()), k=2),
                    "duration_seconds": 8,
                },
            }
        )

    return events
