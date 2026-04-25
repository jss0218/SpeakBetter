from __future__ import annotations

import base64
import json
import logging
import os

import httpx

logger = logging.getLogger(__name__)

CLAIM_EXTRACTION_PROMPT = """
Analyze this speech transcript and respond with ONLY valid JSON.
No explanation, no markdown, no code blocks. Raw JSON only.

Speech scenario: {scenario}
Transcript: {transcript}
Number of adversarial questions to generate: {question_count}

Return exactly this structure:
{{
  "claims": ["main claim 1", "main claim 2", "main claim 3"],
  "weakest_claim": "the specific claim with least evidence",
  "gap_explanation": "one sentence on why this claim is weak",
  "adversarial_questions": [
    "challenging question 1 targeting the weakest claim, under 35 words, referencing specific content from the transcript"
  ]
}}

Rules:
- Only include claims the speaker actually made
- Each question must be specific to what was said, not generic
- Make the questions distinct from each other and escalate pressure slightly
- Return exactly {question_count} questions when the transcript is long enough
- If transcript has fewer than 80 words, return {{"claims": [], "weakest_claim": "", "gap_explanation": "", "adversarial_questions": []}}
- For investor_pitch scenario: focus on business model and market assumptions
- For job_interview scenario: focus on skill claims and experience assertions
- For classroom scenario: focus on conceptual understanding gaps
- For conference scenario: focus on methodology and evidence quality
""".strip()

FOLLOWUP_PROMPT = """
The speaker gave this answer to a challenging question.
Determine if a follow-up is warranted.
Respond with ONLY valid JSON.

Original question: {original_question}
Speaker's answer: {user_answer}
Speaker's original claims: {claims}

If the answer contains a new logical gap worth challenging:
{{"should_followup": true, "followup_question": "the follow-up question under 25 words"}}

If the answer was satisfactory or addressed the gap:
{{"should_followup": false, "followup_question": ""}}
""".strip()

ELEVENLABS_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"


def _parse_json_payload(raw: str | None) -> dict | None:
    if not raw:
        return None
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Failed to parse Gemini JSON payload")
        return None


async def call_gemini(
    prompt: str,
    timeout_seconds: float = 8.0,
    *,
    temperature: float = 0.3,
    max_output_tokens: int = 1024,
) -> str | None:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set")
        return None

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-1.5-flash:generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
            "responseMimeType": "application/json",
        },
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(url, json=payload)
        if response.status_code != 200:
            logger.warning("Gemini non-200 status: %s %s", response.status_code, response.text)
            return None
        body = response.json()
        candidates = body.get("candidates", [])
        if not candidates:
            return None
        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            return None
        return str(parts[0].get("text", "")).strip() or None
    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError, ValueError) as exc:
        logger.warning("Gemini call failed: %s", exc)
        return None


def _normalize_question_count(question_count: int) -> int:
    return max(1, min(10, int(question_count)))


def _sanitize_questions(raw_questions: object, question_count: int) -> list[str]:
    if not isinstance(raw_questions, list):
        return []
    cleaned: list[str] = []
    for item in raw_questions:
        question = " ".join(str(item or "").split()).strip()
        if question and question not in cleaned:
            cleaned.append(question)
        if len(cleaned) >= question_count:
            break
    return cleaned


async def extract_claims_and_questions(
    transcript: str,
    scenario: str,
    question_count: int = 1,
) -> dict | None:
    normalized_count = _normalize_question_count(question_count)
    prompt = CLAIM_EXTRACTION_PROMPT.format(
        scenario=scenario,
        transcript=transcript,
        question_count=normalized_count,
    )
    raw = await call_gemini(prompt=prompt, timeout_seconds=10.0, max_output_tokens=1400)
    parsed = _parse_json_payload(raw)
    if not parsed:
        return None

    required = {"claims", "weakest_claim", "gap_explanation", "adversarial_questions"}
    if not required.issubset(parsed.keys()):
        return None

    claims = parsed.get("claims")
    if not isinstance(claims, list):
        return None
    questions = _sanitize_questions(parsed.get("adversarial_questions"), normalized_count)

    return {
        "claims": [str(c).strip() for c in claims if str(c).strip()],
        "weakest_claim": str(parsed.get("weakest_claim", "")).strip(),
        "gap_explanation": str(parsed.get("gap_explanation", "")).strip(),
        "adversarial_questions": questions,
        "adversarial_question": questions[0] if questions else "",
    }


async def extract_claims_and_question(transcript: str, scenario: str) -> dict | None:
    return await extract_claims_and_questions(transcript=transcript, scenario=scenario, question_count=1)


async def generate_followup_question(
    original_question: str,
    user_answer: str,
    claims: list[str],
) -> str | None:
    prompt = FOLLOWUP_PROMPT.format(
        original_question=original_question,
        user_answer=user_answer,
        claims=json.dumps(claims, ensure_ascii=True),
    )
    raw = await call_gemini(prompt=prompt, timeout_seconds=6.0, max_output_tokens=300)
    parsed = _parse_json_payload(raw)
    if not parsed:
        return None

    if bool(parsed.get("should_followup")):
        question = str(parsed.get("followup_question", "")).strip()
        return question or None
    return None


async def synthesize_question_audio(question: str, api_key: str) -> str | None:
    text = " ".join((question or "").split()).strip()
    if not text or not api_key:
        return None

    payload = {
        "text": text,
        "model_id": "eleven_flash_v2_5",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            logger.warning("ElevenLabs non-200 for argument question audio: %s", response.status_code)
            return None
        return base64.b64encode(response.content).decode("ascii")
    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError) as exc:
        logger.warning("ElevenLabs question audio failed: %s", exc)
        return None
