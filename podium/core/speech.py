from __future__ import annotations

import re
from statistics import quantiles

FILLER_WORDS = [
    "um",
    "uh",
    "like",
    "basically",
    "literally",
    "you know",
    "kind of",
    "sort of",
    "actually",
    "right",
    "so",
    "okay so",
    "and um",
    "i mean",
    "umm",
    "uhhh"
]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _linear(value: float, x0: float, x1: float, y0: float, y1: float) -> float:
    if x1 == x0:
        return y1
    if value <= x0:
        return y0
    if value >= x1:
        return y1
    ratio = (value - x0) / (x1 - x0)
    return y0 + ratio * (y1 - y0)


def count_fillers(text: str) -> tuple[int, list[str]]:
    normalized = (text or "").lower()
    found: list[str] = []
    total = 0

    for filler in FILLER_WORDS:
        pattern = r"\b" + re.escape(filler) + r"\b"
        matches = re.findall(pattern, normalized)
        if matches:
            found.append(filler)
            total += len(matches)

    return total, found


def calculate_wpm(word_count: int, elapsed_seconds: float) -> float:
    if elapsed_seconds < 1 or word_count <= 0:
        return 0.0
    return float(word_count) / (elapsed_seconds / 60.0)


def calculate_pace_score(wpm: float) -> float:
    wpm = max(0.0, float(wpm))
    if wpm <= 80 or wpm >= 220:
        return 0.0
    if 130 <= wpm <= 150:
        return 1.0
    if 110 <= wpm < 130:
        return _linear(wpm, 110, 130, 0.8, 1.0)
    if 150 < wpm <= 170:
        return _linear(wpm, 150, 170, 1.0, 0.8)
    if 90 <= wpm < 110:
        return _linear(wpm, 90, 110, 0.6, 0.8)
    if 170 < wpm <= 190:
        return _linear(wpm, 170, 190, 0.8, 0.6)
    if 80 < wpm < 90:
        return _linear(wpm, 80, 90, 0.0, 0.6)
    return _linear(wpm, 190, 220, 0.6, 0.0)


def calculate_filler_score(filler_rate: float) -> float:
    rate = max(0.0, float(filler_rate))
    if rate <= 2:
        return 1.0
    if rate <= 5:
        return _linear(rate, 2, 5, 1.0, 0.5)
    if rate <= 8:
        return _linear(rate, 5, 8, 0.5, 0.1)
    return 0.0


def calculate_pause_score(pause_count: int, elapsed_seconds: float) -> float:
    if elapsed_seconds <= 0:
        return 1.0
    ppm = float(max(0, pause_count)) / (elapsed_seconds / 60.0)
    if ppm <= 3:
        return 1.0
    if ppm <= 6:
        return 0.7
    if ppm <= 10:
        return 0.4
    return 0.1


def normalize_amplitude(raw_amplitude: float, history: list[float]) -> float:
    raw = max(0.0, float(raw_amplitude))
    baseline = [max(0.0, float(v)) for v in history if v is not None]

    if len(baseline) < 5:
        return _clamp(raw)

    qs = quantiles(baseline, n=20, method="inclusive")
    p05 = qs[0]
    p95 = qs[-1]
    if p95 <= p05:
        return _clamp(raw)

    return _clamp((raw - p05) / (p95 - p05))
