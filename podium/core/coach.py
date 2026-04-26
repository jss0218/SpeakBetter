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


def _build_fallback_moments(session_snapshot: dict) -> tuple[list[dict], list[dict]]:
    transcript_entries = [
        entry for entry in session_snapshot.get("transcript", [])
        if isinstance(entry, dict) and str(entry.get("text", "")).strip()
    ]
    engagement_history = [
        entry for entry in session_snapshot.get("engagement_history", [])
        if isinstance(entry, dict)
    ]

    high_moments: list[dict] = []
    low_moments: list[dict] = []

    for entry in engagement_history:
        score = float(entry.get("score", 0.0))
        timestamp = float(entry.get("timestamp", 0.0))
        signal = str(entry.get("dominant_signal", "")).strip()
        if score >= 0.7 and len(high_moments) < 2:
            high_moments.append(
                {
                    "timestamp_seconds": round(timestamp, 1),
                    "description": f"Audience engagement climbed during {signal.replace('_', ' ') or 'a strong section'}.",
                    "transcript_snippet": "",
                }
            )
        elif score <= 0.42 and len(low_moments) < 2:
            low_moments.append(
                {
                    "timestamp_seconds": round(timestamp, 1),
                    "description": f"Engagement dropped during {signal.replace('_', ' ') or 'a weaker stretch'}.",
                    "transcript_snippet": "",
                }
            )

    for entry in transcript_entries:
        text = str(entry.get("text", "")).strip()
        timestamp = float(entry.get("timestamp", 0.0))
        cumulative_fillers = int(entry.get("cumulative_fillers", 0))
        lowered = text.lower()

        if len(high_moments) < 3 and len(text.split()) >= 8 and cumulative_fillers <= 2:
            high_moments.append(
                {
                    "timestamp_seconds": round(timestamp, 1),
                    "description": "Clear, sustained delivery landed well here.",
                    "transcript_snippet": _snippet(text),
                }
            )

        if len(low_moments) < 3 and (
            any(token in lowered for token in [" um ", " uh ", " like ", " you know ", " i mean "])
            or len(text.split()) <= 4
        ):
            low_moments.append(
                {
                    "timestamp_seconds": round(timestamp, 1),
                    "description": "This section sounded less polished and likely weakened momentum.",
                    "transcript_snippet": _snippet(text),
                }
            )

        if len(high_moments) >= 3 and len(low_moments) >= 3:
            break

    if not high_moments and transcript_entries:
        first = transcript_entries[0]
        high_moments.append(
            {
                "timestamp_seconds": round(float(first.get("timestamp", 0.0)), 1),
                "description": "You established the session with a usable opening.",
                "transcript_snippet": _snippet(str(first.get("text", ""))),
            }
        )

    if not low_moments and transcript_entries:
        last = transcript_entries[-1]
        low_moments.append(
            {
                "timestamp_seconds": round(float(last.get("timestamp", 0.0)), 1),
                "description": "The close still needed sharper evidence and cleaner phrasing.",
                "transcript_snippet": _snippet(str(last.get("text", ""))),
            }
        )

    def dedupe(moments: list[dict]) -> list[dict]:
        seen: set[tuple[int, str]] = set()
        cleaned: list[dict] = []
        for moment in moments:
            key = (int(float(moment.get("timestamp_seconds", 0.0))), str(moment.get("description", "")))
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(moment)
        return cleaned[:3]

    return dedupe(high_moments), dedupe(low_moments)


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

    try:
        normalized["overall_score"] = int(max(0, min(100, round(float(normalized.get("overall_score", fallback["overall_score"]))))))
    except Exception:
        normalized["overall_score"] = fallback["overall_score"]

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
    avg_engagement = float(session_snapshot.get("engagement_score", 0.0))
    overall_score = int(max(0, min(100, round(avg_engagement * 100))))
    filler_count = int(session_snapshot.get("filler_count", 0))
    wpm = float(session_snapshot.get("words_per_minute", 0.0))
    eye = float(session_snapshot.get("eye_contact_score", 0.0))
    posture = float(session_snapshot.get("posture_score", 0.5))
    gesture = float(session_snapshot.get("gesture_score", 0.4))
    motion = float(session_snapshot.get("motion_score", 0.0))
    brow = float(session_snapshot.get("brow_furrow", 0.0))

    strengths: list[str] = []
    improvements: list[str] = []

    strengths.append("Maintained composure through the session")
    strengths.append("Completed the speaking run with full transcript coverage")
    strengths.append("Handled dynamic audience pressure events")

    if filler_count > 15:
        improvements.append("Reduce filler words — use deliberate pauses instead")
    if wpm < 110:
        improvements.append("Increase speaking pace to maintain momentum")
    elif wpm > 170:
        improvements.append("Slow down slightly to improve clarity")
    if eye < 0.6:
        improvements.append("Improve eye contact consistency with the camera")
    if posture < 0.55:
        improvements.append("Stand taller and keep shoulders level")
    if gesture < 0.5:
        improvements.append("Use deliberate hand gestures to emphasize key points")
    if motion > 0.55:
        improvements.append("Reduce swaying and reset your feet between points")
    if brow > 0.55:
        improvements.append("Relax facial tension so confidence reads clearly")

    while len(improvements) < 3:
        improvements.append("Tighten claim-evidence links for stronger arguments")

    high_moments, low_moments = _build_fallback_moments(session_snapshot)

    return {
        "overall_score": overall_score,
        "high_moments": high_moments,
        "low_moments": low_moments,
        "strengths": strengths[:3],
        "improvements": improvements[:3],
        "next_session_focus": "Deliver stronger evidence for each major claim.",
        "argument_feedback": "Strengthen the weakest claim with one concrete example.",
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
