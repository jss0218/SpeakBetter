from __future__ import annotations

import base64
import json
import logging
import os

import httpx

from .speech import count_fillers

logger = logging.getLogger(__name__)

REALTIME_TIP_PROMPT = """
You are a direct, no-nonsense public speaking coach giving live feedback.
Give ONE specific tip in under 12 words.
Be direct. Reference actual words from the transcript if possible.
Do not be gentle or use filler phrases like "try to" or "consider".
Just the tip. Nothing else.

Recent speech (last 30 seconds): {recent_transcript}
Current weakness detected: {dominant_signal}
Recent filler words used: {recent_fillers}
""".strip()

BREAKDOWN_PROMPT = """
Analyze this complete public speaking session.
Respond with ONLY valid JSON. No markdown, no explanation.

Session data:
- Scenario: {scenario}
- Duration: {duration} seconds
- Full transcript: {transcript}
- Engagement timeline: {engagement_history}
- Average engagement: {avg_engagement}
- Total filler words: {filler_count}
- Average WPM: {avg_wpm}
- Average eye contact score: {avg_eye_contact}
- Average posture score: {avg_posture}
- Gesture score: {gesture_score}
- Motion balance score: {motion_score}
- Facial expression: {expression}
- Argument gap identified: {weakest_claim}
- Pressure events that fired: {pressure_events}

Return this exact JSON:
{{
  "overall_score": <integer 0-100>,
  "high_moments": [
    {{
      "timestamp_seconds": <float>,
      "description": "<what went well>",
      "transcript_snippet": "<exact words from transcript>"
    }}
  ],
  "low_moments": [
    {{
      "timestamp_seconds": <float>,
      "description": "<what went wrong>",
      "transcript_snippet": "<exact words from transcript>"
    }}
  ],
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "improvements": ["improvement 1", "improvement 2", "improvement 3"],
  "next_session_focus": "<single most important thing, one sentence>",
  "argument_feedback": "<feedback on the logical gap that was found>"
}}
Include 2-3 high moments and 2-3 low moments minimum.
Each description must name what actually happened (e.g. specific filler words, WPM range, or dominant_signal)
and must align with transcript_snippet when you include one.
""".strip()

ELEVENLABS_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"


async def call_gemini(prompt: str, timeout_seconds: float = 10.0) -> str | None:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set")
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024},
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(url, json=payload)
        if response.status_code != 200:
            logger.warning("Gemini non-200: %s %s", response.status_code, response.text)
            return None
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as exc:
        logger.warning("Gemini call failed: %s", exc)
        return None


def _safe_json_parse(raw: str | None) -> dict | None:
    if not raw:
        return None
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _snippet(text: str, word_limit: int = 14) -> str:
    words = (text or "").split()
    if not words:
        return ""
    if len(words) <= word_limit:
        return " ".join(words)
    return " ".join(words[:word_limit]).strip() + "..."


def _nearest_transcript_line(transcript_entries: list[dict], ts: float) -> tuple[float, str]:
    if not transcript_entries:
        return ts, ""
    best = min(
        transcript_entries,
        key=lambda e: abs(float(e.get("timestamp", 0.0)) - ts),
    )
    return float(best.get("timestamp", ts)), str(best.get("text", "")).strip()


def _chunk_filler_meta(entry: dict) -> tuple[int, list[str]]:
    text = str(entry.get("text", "")).strip()
    stored = entry.get("chunk_fillers")
    words = entry.get("filler_words")
    if isinstance(stored, int) and stored >= 0 and isinstance(words, list):
        cleaned = [str(w).strip().lower() for w in words if str(w).strip()]
        return int(stored), cleaned
    total, found = count_fillers(text)
    return int(total), list(found)


def _format_ts(ts: float) -> str:
    ts_int = max(0, int(round(float(ts))))
    mins = ts_int // 60
    secs = ts_int % 60
    return f"{mins}:{secs:02d}"


def _coalesce_moments(moments: list[dict], *, min_gap_s: float, cap: int) -> list[dict]:
    chosen: list[dict] = []
    last_ts: float | None = None
    for m in sorted(moments, key=lambda x: float(x.get("timestamp_seconds", 0.0))):
        ts = float(m.get("timestamp_seconds", 0.0))
        if last_ts is not None and abs(ts - last_ts) < min_gap_s:
            continue
        chosen.append(m)
        last_ts = ts
        if len(chosen) >= cap:
            break
    return chosen


def _balanced_select(
    moments: list[dict],
    *,
    min_gap_s: float,
    cap: int,
    per_kind_cap: dict[str, int],
) -> list[dict]:
    chosen: list[dict] = []
    chosen_ts: list[float] = []
    counts: dict[str, int] = {}

    for m in sorted(moments, key=lambda x: float(x.get("timestamp_seconds", 0.0))):
        ts = float(m.get("timestamp_seconds", 0.0))
        if any(abs(ts - prev) < min_gap_s for prev in chosen_ts):
            continue
        kind = str(m.get("timeline_kind", "") or "")
        limit = per_kind_cap.get(kind, per_kind_cap.get("*", cap))
        if counts.get(kind, 0) >= limit:
            continue
        chosen.append(m)
        chosen_ts.append(ts)
        counts[kind] = counts.get(kind, 0) + 1
        if len(chosen) >= cap:
            break

    return chosen


def _shorten(text: str, max_chars: int = 150) -> str:
    s = " ".join(str(text or "").split()).strip()
    if len(s) <= max_chars:
        return s
    return s[: max(0, max_chars - 1)].rstrip() + "…"


def _build_fallback_moments(session_snapshot: dict) -> tuple[list[dict], list[dict]]:
    transcript_entries = [
        entry
        for entry in session_snapshot.get("transcript", [])
        if isinstance(entry, dict) and str(entry.get("text", "")).strip()
    ]
    engagement_history = [
        entry for entry in session_snapshot.get("engagement_history", []) if isinstance(entry, dict)
    ]
    vision_history = [
        entry for entry in session_snapshot.get("vision_history", []) if isinstance(entry, dict)
    ]

    low_moments: list[dict] = []
    seen_low: set[tuple] = set()

    ignore_low_signal_fillers = {
        "so",
        "right",
        "okay so",
        "okay",
    }
    high_signal_fillers = {
        "um",
        "uh",
        "umm",
        "uhhh",
        "like",
        "you know",
        "i mean",
        "basically",
        "literally",
        "kind of",
        "sort of",
        "actually",
    }

    last_low_at: float | None = None
    for entry in transcript_entries:
        text = str(entry.get("text", "")).strip()
        ts = float(entry.get("timestamp", 0.0))
        if last_low_at is not None and ts - last_low_at < 6.0:
            continue
        n_fill, filler_words = _chunk_filler_meta(entry)
        if n_fill <= 0:
            continue
        ordered = list(dict.fromkeys(filler_words))
        # Avoid spamming low-signal fillers like "so" unless there's something stronger too,
        # or the chunk had multiple fillers.
        if ordered and all(w in ignore_low_signal_fillers for w in ordered) and n_fill < 2:
            continue
        if ordered and not any(w in high_signal_fillers for w in ordered) and n_fill < 2:
            continue
        label = ", ".join(ordered) if ordered else "filler word(s)"
        snippet = _snippet(text, 16)
        desc = f'{_format_ts(ts)} — Used {label}. "{snippet}"'
        key = (round(ts, 1), "filler")
        if key in seen_low:
            continue
        seen_low.add(key)
        low_moments.append(
            {
                "timestamp_seconds": round(ts, 1),
                "description": desc,
                "transcript_snippet": snippet,
                "timeline_kind": "filler",
            }
        )
        last_low_at = ts
        # Surface a few concrete filler moments early (still filtered + spaced).
        if len(low_moments) >= 6:
            break

    for entry in sorted(engagement_history, key=lambda e: float(e.get("score", 0.0))):
        if len(low_moments) >= 10:
            break
        score = float(entry.get("score", 0.0))
        if score > 0.44:
            continue
        ts = float(entry.get("timestamp", 0.0))
        if any(abs(ts - float(m.get("timestamp_seconds", 0.0))) < 8.0 for m in low_moments):
            continue
        signal = str(entry.get("dominant_signal", "")).strip().replace("_", " ") or "delivery"
        nts, line = _nearest_transcript_line(transcript_entries, ts)
        snippet = _snippet(line, 14) if line else ""
        desc = f"{_format_ts(nts)} — Engagement dipped (~{int(round(score * 100))}%, {signal})."
        if snippet:
            desc += f' "{snippet}"'
        key = (round(ts, 1), "eng_low")
        if key in seen_low:
            continue
        seen_low.add(key)
        low_moments.append(
            {
                "timestamp_seconds": round(nts, 1),
                "description": desc,
                "transcript_snippet": snippet,
                "timeline_kind": "engagement",
            }
        )

    high_moments: list[dict] = []
    seen_high: set[tuple] = set()

    last_high_at: float | None = None
    for entry in transcript_entries:
        text = str(entry.get("text", "")).strip()
        ts = float(entry.get("timestamp", 0.0))
        if last_high_at is not None and ts - last_high_at < 10.0:
            continue
        words = text.split()
        if len(words) < 6:
            continue
        n_fill, _ = _chunk_filler_meta(entry)
        if n_fill > 0:
            continue
        wpm_val = float(entry.get("wpm", 0.0) or 0.0)
        if not (112.0 <= wpm_val <= 168.0):
            continue
        snippet = _snippet(text, 16)
        desc = f'{_format_ts(ts)} — Clean pace (~{int(round(wpm_val))} WPM), no fillers. "{snippet}"'
        key = (round(ts, 1), "pace")
        if key in seen_high:
            continue
        seen_high.add(key)
        high_moments.append(
            {
                "timestamp_seconds": round(ts, 1),
                "description": desc,
                "transcript_snippet": snippet,
                "timeline_kind": "pace",
            }
        )
        last_high_at = ts
        if len(high_moments) >= 4:
            break

    for entry in sorted(engagement_history, key=lambda e: -float(e.get("score", 0.0))):
        if len(high_moments) >= 8:
            break
        score = float(entry.get("score", 0.0))
        if score < 0.7:
            continue
        ts = float(entry.get("timestamp", 0.0))
        if any(abs(ts - float(m.get("timestamp_seconds", 0.0))) < 10.0 for m in high_moments):
            continue
        signal = str(entry.get("dominant_signal", "")).strip().replace("_", " ") or "delivery"
        nts, line = _nearest_transcript_line(transcript_entries, ts)
        snippet = _snippet(line, 14) if line else ""
        desc = f"{_format_ts(nts)} — Engagement peaked (~{int(round(score * 100))}%, {signal})."
        if snippet:
            desc += f' "{snippet}"'
        key = (round(ts, 1), "eng_high")
        if key in seen_high:
            continue
        seen_high.add(key)
        high_moments.append(
            {
                "timestamp_seconds": round(nts, 1),
                "description": desc,
                "transcript_snippet": snippet,
                "timeline_kind": "engagement",
            }
        )

    eye_added = 0
    for entry in sorted(vision_history, key=lambda e: -float(e.get("eye_contact", 0.0) or 0.0)):
        if len(high_moments) >= 9:
            break
        if not bool(entry.get("face_detected", False)):
            continue
        eye = float(entry.get("eye_contact", 0.0) or 0.0)
        if eye < 0.85:
            continue
        ts = float(entry.get("timestamp", 0.0))
        if any(abs(ts - float(m.get("timestamp_seconds", 0.0))) < 10.0 for m in high_moments):
            continue
        nts, line = _nearest_transcript_line(transcript_entries, ts)
        # Only surface eye-contact moments when there's a real spoken beat nearby
        # (otherwise we get lots of tiny fragments like "oh yeah").
        if len((line or "").split()) < 6:
            continue
        snippet = _snippet(line, 14) if line else ""
        desc = f"{_format_ts(nts)} — Eye contact strong (~{int(round(eye * 100))}%)."
        if snippet:
            desc += f' "{snippet}"'
        key = (round(ts, 1), "eye")
        if key in seen_high:
            continue
        seen_high.add(key)
        high_moments.append(
            {
                "timestamp_seconds": round(nts, 1),
                "description": desc,
                "transcript_snippet": snippet,
                "timeline_kind": "eye_contact",
            }
        )
        eye_added += 1
        if eye_added >= 2:
            break

    if not high_moments and transcript_entries:
        first = transcript_entries[0]
        t0 = float(first.get("timestamp", 0.0))
        tx = str(first.get("text", "")).strip()
        high_moments.append(
            {
                "timestamp_seconds": round(t0, 1),
                "description": f'Opening beat: "{_snippet(tx, 22)}"',
                "transcript_snippet": _snippet(tx, 22),
                "timeline_kind": "pace",
            }
        )

    if not low_moments and transcript_entries:
        last = transcript_entries[-1]
        t1 = float(last.get("timestamp", 0.0))
        tx = str(last.get("text", "")).strip()
        low_moments.append(
            {
                "timestamp_seconds": round(t1, 1),
                "description": f'Last stretch to review: "{_snippet(tx, 22)}"',
                "transcript_snippet": _snippet(tx, 22),
                "timeline_kind": "pace",
            }
        )

    def dedupe_sorted(moments: list[dict], cap: int) -> list[dict]:
        seen_keys: set[tuple] = set()
        cleaned: list[dict] = []
        for moment in sorted(
            moments,
            key=lambda m: float(m.get("timestamp_seconds", 0.0)),
        ):
            tsf = round(float(moment.get("timestamp_seconds", 0.0)), 1)
            kind = str(moment.get("timeline_kind", "") or "")
            snip = str(moment.get("transcript_snippet", "") or "")[:24]
            key = (tsf, kind, snip)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            cleaned.append(moment)
            if len(cleaned) >= cap:
                break
        return cleaned

    highs = dedupe_sorted(high_moments, 20)
    lows = dedupe_sorted(low_moments, 26)
    highs = _balanced_select(
        highs,
        min_gap_s=8.0,
        cap=10,
        per_kind_cap={
            "pace": 4,
            "engagement": 4,
            "eye_contact": 2,
            "*": 3,
        },
    )
    lows = _balanced_select(
        lows,
        min_gap_s=6.0,
        cap=12,
        per_kind_cap={
            "filler": 7,
            "engagement": 5,
            "*": 4,
        },
    )
    for m in highs + lows:
        if isinstance(m, dict) and "description" in m:
            m["description"] = _shorten(str(m.get("description", "")), 170)
    return highs, lows


_GENERIC_MOMENT_PHRASES = (
    "clear, sustained delivery landed well here",
    "this section sounded less polished",
)


def _enrich_moment_descriptions(moments: list[dict]) -> list[dict]:
    out: list[dict] = []
    for moment in moments:
        if not isinstance(moment, dict):
            continue
        m = dict(moment)
        desc = str(m.get("description", "")).strip()
        snip = str(m.get("transcript_snippet", "")).strip()
        dlow = desc.lower()
        if snip and any(p in dlow for p in _GENERIC_MOMENT_PHRASES):
            m["description"] = f'{desc} Evidence from your transcript: "{_snippet(snip, 20)}"'
        out.append(m)
    return out


def _normalize_breakdown(parsed: dict, session_snapshot: dict) -> dict:
    fallback = fallback_breakdown(session_snapshot)
    normalized = dict(fallback)
    normalized.update({k: v for k, v in parsed.items() if v is not None})

    high_moments = normalized.get("high_moments")
    low_moments = normalized.get("low_moments")
    if not isinstance(high_moments, list) or not high_moments:
        normalized["high_moments"] = fallback["high_moments"]
    if not isinstance(low_moments, list) or not low_moments:
        normalized["low_moments"] = fallback["low_moments"]

    for key in ["strengths", "improvements"]:
        value = normalized.get(key)
        if not isinstance(value, list) or not value:
            normalized[key] = fallback[key]

    if not normalized.get("next_session_focus"):
        normalized["next_session_focus"] = fallback["next_session_focus"]
    if not normalized.get("argument_feedback"):
        normalized["argument_feedback"] = fallback["argument_feedback"]

    hm_final = normalized.get("high_moments")
    lm_final = normalized.get("low_moments")
    if isinstance(hm_final, list):
        normalized["high_moments"] = _enrich_moment_descriptions(
            [dict(x) for x in hm_final if isinstance(x, dict)]
        )
    if isinstance(lm_final, list):
        normalized["low_moments"] = _enrich_moment_descriptions(
            [dict(x) for x in lm_final if isinstance(x, dict)]
        )

    # If the model returned only a couple of moments, supplement with fallback moments
    # so the UI timeline doesn't look empty.
    def _merge_moments(primary: list[dict], extra: list[dict], min_count: int) -> list[dict]:
        out: list[dict] = []
        seen: set[tuple] = set()
        for src in (primary, extra):
            for m in src:
                if not isinstance(m, dict):
                    continue
                ts = round(float(m.get("timestamp_seconds", 0.0) or 0.0), 1)
                kind = str(m.get("timeline_kind", "") or "")
                snip = str(m.get("transcript_snippet", "") or "")[:24]
                key = (ts, kind, snip)
                if key in seen:
                    continue
                seen.add(key)
                out.append(m)
        return out if len(out) >= min_count else out

    try:
        hm_enriched = normalized.get("high_moments") if isinstance(normalized.get("high_moments"), list) else []
        lm_enriched = normalized.get("low_moments") if isinstance(normalized.get("low_moments"), list) else []
        if isinstance(hm_enriched, list) and len(hm_enriched) < 4:
            normalized["high_moments"] = _merge_moments(hm_enriched, fallback.get("high_moments", []), min_count=4)
        if isinstance(lm_enriched, list) and len(lm_enriched) < 4:
            normalized["low_moments"] = _merge_moments(lm_enriched, fallback.get("low_moments", []), min_count=4)
    except Exception:
        # Non-fatal; keep whatever we have.
        pass

    def _score_from_engagement(avg: float) -> int:
        x = max(0.0, min(1.0, float(avg)))
        # Slightly lenient curve: mid-range sessions score a bit higher,
        # while weak sessions still stay low.
        curved = x ** 0.85
        return int(max(0, min(100, round(curved * 100))))

    try:
        parsed_score = float(normalized.get("overall_score", fallback["overall_score"]))
    except Exception:
        parsed_score = float(fallback["overall_score"])
    computed_score = _score_from_engagement(float(normalized.get("avg_engagement", fallback.get("avg_engagement", 0.0))))
    # Blend toward computed to avoid "always low" model output, but keep it tied to the session.
    blended = 0.65 * float(parsed_score) + 0.35 * float(computed_score)
    normalized["overall_score"] = int(max(0, min(100, round(blended))))

    # Ensure metric fields are present so the UI never needs to guess.
    for key in ["avg_engagement", "filler_count", "filler_words", "avg_wpm", "avg_eye_contact", "key_insight", "overall_tips"]:
        if key not in normalized or normalized.get(key) is None:
            normalized[key] = fallback.get(key)

    # If the model returns generic strengths (or empty), prefer metric-derived strengths
    # to keep them session-specific and consistent with the UI stats.
    def _is_generic_strength(s: str) -> bool:
        low = (s or "").strip().lower()
        return any(
            p in low
            for p in [
                "maintained composure",
                "completed the speaking run",
                "handled dynamic audience",
                "good job",
                "great job",
                "well done",
            ]
        )

    strengths_val = normalized.get("strengths")
    if not isinstance(strengths_val, list) or not strengths_val or all(_is_generic_strength(str(x)) for x in strengths_val):
        normalized["strengths"] = fallback.get("strengths", [])[:3]

    return normalized


async def generate_realtime_tip(
    recent_transcript: str,
    dominant_signal: str,
    coach_tips: list[dict],
    last_tip_timestamp: float,
    current_timestamp: float,
) -> str | None:
    del coach_tips

    if current_timestamp - float(last_tip_timestamp) < 25:
        return None

    transcript = (recent_transcript or "").strip()
    if len(transcript.split()) < 20:
        return None

    _, filler_words = count_fillers(transcript)
    prompt = REALTIME_TIP_PROMPT.format(
        recent_transcript=transcript,
        dominant_signal=dominant_signal,
        recent_fillers=", ".join(filler_words) if filler_words else "none",
    )

    raw = await call_gemini(prompt=prompt, timeout_seconds=3)
    tip = (raw or "").strip()
    if not tip:
        return None
    return " ".join(tip.split())


def generate_vision_tip(
    recent_vision: list[dict],
    last_signal: str = "",
    delivery_events: list[dict] | None = None,
    vision_confidence: float = 1.0,
) -> tuple[str | None, str]:
    delivery_events = delivery_events or []
    if delivery_events and vision_confidence >= 0.4:
        event = delivery_events[0]
        signal = str(event.get("name", ""))
        tip = str(event.get("tip", "")).strip()
        if tip and signal != last_signal:
            return tip, signal
        return None, last_signal

    if len(recent_vision) < 8:
        return None, last_signal

    face_samples = [entry for entry in recent_vision if entry.get("face_detected")]
    if len(face_samples) < max(4, len(recent_vision) // 2):
        signal = "no_face"
        if signal != last_signal:
            return "Step back into frame so the audience can read you.", signal
        return None, last_signal

    count = len(face_samples)
    avg_eye = sum(float(entry.get("eye_contact", 0.5)) for entry in face_samples) / count
    avg_posture = sum(float(entry.get("posture_score", 0.5)) for entry in face_samples) / count
    avg_motion = sum(float(entry.get("motion_score", 0.0)) for entry in face_samples) / count
    avg_brow = sum(float(entry.get("brow_furrow", 0.0)) for entry in face_samples) / count
    gesture_rate = sum(1 for entry in face_samples if entry.get("gesture_detected")) / count

    candidates: list[tuple[str, str, float]] = []
    if avg_eye < 0.4:
        candidates.append(("low_eye_contact", "Look up from your notes and address the camera.", 0.4 - avg_eye))
    if avg_posture < 0.45:
        candidates.append(("poor_posture", "Straighten your shoulders and plant your stance.", 0.45 - avg_posture))
    if gesture_rate < 0.08:
        candidates.append(("stiff_gestures", "Use one deliberate hand gesture on your next point.", 0.08 - gesture_rate))
    elif gesture_rate > 0.75:
        candidates.append(("excessive_gestures", "Quiet your hands and hold still between points.", gesture_rate - 0.75))
    if avg_motion > 0.55:
        candidates.append(("fidgeting", "Reduce the swaying; reset your feet before continuing.", avg_motion - 0.55))
    if avg_brow > 0.55:
        candidates.append(("tense_expression", "Relax your brow so confidence shows on your face.", avg_brow - 0.55))

    if not candidates:
        return None, ""

    signal, tip, _ = max(candidates, key=lambda item: item[2])
    if signal == last_signal:
        return None, last_signal
    return tip, signal


async def generate_session_breakdown(session_snapshot: dict) -> dict:
    engagement_history = session_snapshot.get("engagement_history", [])
    eye_samples = [
        float(entry.get("score", 0.0))
        for entry in engagement_history
        if isinstance(entry, dict)
    ]
    avg_engagement = (
        sum(eye_samples) / len(eye_samples)
        if eye_samples
        else float(session_snapshot.get("engagement_score", 0.0))
    )

    prompt = BREAKDOWN_PROMPT.format(
        scenario=session_snapshot.get("scenario", "investor_pitch"),
        duration=round(float(session_snapshot.get("elapsed_seconds", 0.0)), 2),
        transcript=session_snapshot.get("full_transcript", ""),
        engagement_history=json.dumps(engagement_history, ensure_ascii=True),
        avg_engagement=round(avg_engagement, 3),
        filler_count=int(session_snapshot.get("filler_count", 0)),
        avg_wpm=round(float(session_snapshot.get("words_per_minute", 0.0)), 2),
        avg_eye_contact=round(float(session_snapshot.get("eye_contact_score", 0.0)), 3),
        avg_posture=round(float(session_snapshot.get("posture_score", 0.0)), 3),
        gesture_score=round(float(session_snapshot.get("gesture_score", 0.0)), 3),
        motion_score=round(float(session_snapshot.get("motion_score", 0.0)), 3),
        expression=session_snapshot.get("expression", "neutral"),
        weakest_claim=session_snapshot.get("weakest_claim", ""),
        pressure_events=json.dumps(
            session_snapshot.get("pressure_events_fired", []), ensure_ascii=True
        ),
    )

    raw = await call_gemini(prompt=prompt, timeout_seconds=20)
    parsed = _safe_json_parse(raw)
    if not parsed:
        return fallback_breakdown(session_snapshot)
    return _normalize_breakdown(parsed, session_snapshot)


def fallback_breakdown(session_snapshot: dict) -> dict:
    engagement_history = session_snapshot.get("engagement_history", []) or []
    samples = [
        float(entry.get("score", 0.0))
        for entry in engagement_history
        if isinstance(entry, dict)
    ]
    avg_engagement = (sum(samples) / len(samples)) if samples else float(session_snapshot.get("engagement_score", 0.0))
    overall_score = int(max(0, min(100, round((max(0.0, min(1.0, avg_engagement)) ** 0.85) * 100))))
    filler_count = int(session_snapshot.get("filler_count", 0))
    wpm = float(session_snapshot.get("words_per_minute", 0.0))
    eye = float(session_snapshot.get("eye_contact_score", 0.0))
    posture = float(session_snapshot.get("posture_score", 0.5))
    gesture = float(session_snapshot.get("gesture_score", 0.4))
    motion = float(session_snapshot.get("motion_score", 0.0))
    brow = float(session_snapshot.get("brow_furrow", 0.0))
    # Derive common filler words from transcript evidence (avoids mismatches like
    # filler_count > 0 but filler_words empty).
    filler_word_counts: dict[str, int] = {}
    for entry in session_snapshot.get("transcript", []) or []:
        if not isinstance(entry, dict):
            continue
        for w in entry.get("filler_words", []) or []:
            sw = str(w or "").strip().lower()
            if not sw:
                continue
            filler_word_counts[sw] = filler_word_counts.get(sw, 0) + 1
    filler_words = [w for w, _ in sorted(filler_word_counts.items(), key=lambda kv: (-kv[1], kv[0]))][:8]
    pressure_events = session_snapshot.get("pressure_events_fired", []) or []
    dominant_signal = str(session_snapshot.get("dominant_signal", "") or "").strip()
    delivery_events = session_snapshot.get("delivery_events", []) or []

    high_moments, low_moments = _build_fallback_moments(session_snapshot)

    strengths: list[str] = []
    overall_tips: list[str] = []

    # Prefer transcript-backed moments (unique per run) over template metrics.
    # Strengths: pick up to 2 distinct "high" beats.
    seen_kinds: set[str] = set()
    for moment in (high_moments or []):
        if not isinstance(moment, dict):
            continue
        kind = str(moment.get("timeline_kind", "") or "").strip()
        snip = str(moment.get("transcript_snippet", "") or "").strip()
        if not snip or len(snip.split()) < 4:
            continue
        if kind and kind in seen_kinds:
            continue
        seen_kinds.add(kind)
        pretty = kind.replace("_", " ")
        strengths.append(f'Strong {pretty} at key moments (e.g. "{_snippet(snip, 16)}")')
        if len(strengths) >= 2:
            break

    # Tips: pick up to 2 distinct "low" beats.
    seen_low_kinds: set[str] = set()
    for moment in (low_moments or []):
        if not isinstance(moment, dict):
            continue
        kind = str(moment.get("timeline_kind", "") or "").strip()
        snip = str(moment.get("transcript_snippet", "") or "").strip()
        if not snip or len(snip.split()) < 4:
            continue
        if kind and kind in seen_low_kinds:
            continue
        seen_low_kinds.add(kind)
        pretty = kind.replace("_", " ")
        overall_tips.append(f'Improve {pretty} consistency (watch moments like "{_snippet(snip, 16)}")')
        if len(overall_tips) >= 2:
            break

    # If moments weren't available, fall back to metric-derived guidance (still tied to the run).
    if not strengths:
        if filler_count <= 5:
            strengths.append(f"Minimal filler words ({filler_count} total)")
        if 120 <= wpm <= 165:
            strengths.append(f"Steady speaking pace (~{int(round(wpm))} WPM)")
        if eye >= 0.7:
            strengths.append(f"Consistent eye contact (≈{int(round(eye * 100))}%)")
        if posture >= 0.62:
            strengths.append("Strong posture and stable presence")
        if gesture >= 0.58:
            strengths.append("Gestures supported key points without distracting")
        if pressure_events:
            strengths.append("Handled dynamic audience pressure events")

    if len(overall_tips) < 2:
        if wpm < 110:
            overall_tips.append("Increase speaking pace to maintain momentum")
        elif wpm > 170:
            overall_tips.append("Slow down slightly to improve clarity")
        if filler_count > 15:
            overall_tips.append("Reduce filler words — use deliberate pauses instead")
        if eye < 0.6:
            overall_tips.append("Improve eye contact consistency with the camera")

    strengths = list(dict.fromkeys([s for s in strengths if s]))[:3]

    # Build a single key insight + a few tips that reflect this exact session.
    key_insight = ""
    if dominant_signal in {"too_fast", "too_slow"}:
        key_insight = f"Your pace was {dominant_signal.replace('_', ' ')} — aim for 120–165 WPM."
    elif dominant_signal in {"high_filler_rate"}:
        key_insight = "Fillers are the main leak — replace them with short, silent pauses."
    elif dominant_signal in {"poor_eye_contact"}:
        key_insight = "Bring your gaze back to the camera more often to keep attention."
    else:
        key_insight = "Keep your strongest delivery habits consistent throughout the full session."

    # Pull in a couple of session coach tips (these vary run-to-run).
    coach_tip_texts: list[str] = []
    for tip_entry in (session_snapshot.get("coach_tips", []) or []):
        if not isinstance(tip_entry, dict):
            continue
        t = str(tip_entry.get("tip", "") or "").strip()
        if t:
            coach_tip_texts.append(t)
    for tip in coach_tip_texts[-4:]:
        overall_tips.append(tip)

    return {
        "overall_score": overall_score,
        "avg_engagement": avg_engagement,
        "filler_count": filler_count,
        "filler_words": filler_words if isinstance(filler_words, list) else [],
        "avg_wpm": wpm,
        "avg_eye_contact": eye,
        "high_moments": high_moments,
        "low_moments": low_moments,
        "strengths": strengths[:3],
        "improvements": list(dict.fromkeys([t for t in overall_tips if t]))[:3],
        "next_session_focus": "Deliver stronger evidence for each major claim.",
        "argument_feedback": "Strengthen the weakest claim with one concrete example.",
        "key_insight": key_insight,
        "overall_tips": list(dict.fromkeys([t for t in overall_tips if t]))[:3],
    }


async def voice_tip(tip: str, api_key: str) -> str | None:
    if not api_key:
        return None

    payload = {
        "text": tip,
        "model_id": "eleven_flash_v2_5",  # upgraded from eleven_monolingual_v1
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            logger.warning("ElevenLabs non-200: %s", response.status_code)
            return None
        return base64.b64encode(response.content).decode("ascii")
    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError) as exc:
        logger.warning("ElevenLabs voice failed: %s", exc)
        return None
