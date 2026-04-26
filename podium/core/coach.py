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
- Argument gap identified: {weakest_claim}

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


async def call_groq(
    prompt: str,
    timeout_seconds: float = 10.0,
    *,
    temperature: float = 0.7,
    max_output_tokens: int = 1024,
) -> str | None:
    api_key = os.getenv("GROQ_API_KEY", "")
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip() or "llama-3.3-70b-versatile"
    if not api_key:
        logger.warning("GROQ_API_KEY not set")
        return None

    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_output_tokens,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            logger.warning("Groq non-200: %s %s", response.status_code, response.text)
            return None
        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            return None
        message = choices[0].get("message", {})
        return str(message.get("content", "")).strip() or None
    except Exception as exc:
        logger.warning("Groq call failed: %s", exc)
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

    raw = await call_groq(prompt=prompt, timeout_seconds=3, max_output_tokens=128)
    tip = (raw or "").strip()
    if not tip:
        return None
    return " ".join(tip.split())


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
        scenario=session_snapshot.get("scenario", "pitch"),
        duration=round(float(session_snapshot.get("elapsed_seconds", 0.0)), 2),
        transcript=session_snapshot.get("full_transcript", ""),
        engagement_history=json.dumps(engagement_history, ensure_ascii=True),
        avg_engagement=round(avg_engagement, 3),
        filler_count=int(session_snapshot.get("filler_count", 0)),
        avg_wpm=round(float(session_snapshot.get("words_per_minute", 0.0)), 2),
        avg_eye_contact=round(float(session_snapshot.get("eye_contact_score", 0.0)), 3),
        weakest_claim=session_snapshot.get("weakest_claim", ""),
    )

    raw = await call_groq(
        prompt=prompt,
        timeout_seconds=20,
        temperature=0.3,
        max_output_tokens=1400,
    )
    parsed = _safe_json_parse(raw)
    if not parsed:
        return fallback_breakdown(session_snapshot)
    return parsed


def fallback_breakdown(session_snapshot: dict) -> dict:
    avg_engagement = float(session_snapshot.get("engagement_score", 0.0))
    overall_score = int(max(0, min(100, round(avg_engagement * 100))))
    filler_count = int(session_snapshot.get("filler_count", 0))
    wpm = float(session_snapshot.get("words_per_minute", 0.0))
    eye = float(session_snapshot.get("eye_contact_score", 0.0))

    strengths: list[str] = []
    improvements: list[str] = []

    strengths.append("Maintained composure through the session")
    strengths.append("Completed the speaking run with full transcript coverage")
    strengths.append("Sustained a complete speaking run from start to finish")

    if filler_count > 15:
        improvements.append("Reduce filler words — use deliberate pauses instead")
    if wpm < 110:
        improvements.append("Increase speaking pace to maintain momentum")
    elif wpm > 170:
        improvements.append("Slow down slightly to improve clarity")
    if eye < 0.6:
        improvements.append("Improve eye contact consistency with the camera")

    while len(improvements) < 3:
        improvements.append("Tighten claim-evidence links for stronger arguments")

    return {
        "overall_score": overall_score,
        "high_moments": [],
        "low_moments": [],
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
