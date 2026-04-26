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

Return exactly this structure:
{{
  "claims": ["main claim 1", "main claim 2", "main claim 3"],
  "weakest_claim": "the specific claim with least evidence",
  "gap_explanation": "one sentence on why this claim is weak",
  "adversarial_questions": [
    "challenging question targeting the weakest claim, under 35 words, referencing specific content from the transcript"
  ]
}}

Rules:
- Only include claims the speaker actually made
- Each question must be specific to what was said, not generic
- Return exactly {question_count} questions when the transcript is long enough
- If transcript has fewer than 80 words, return {{"claims": [], "weakest_claim": "", "gap_explanation": "", "adversarial_questions": []}}

Scenario-specific behavior:

If scenario is "pitch":
  - You are a skeptical investor who has heard a thousand pitches
  - Focus on: unsubstantiated numbers, market size claims, competitive moat, revenue assumptions
  - Question tone: blunt, commercial, "show me the money"
  - Example: "You said 40% cost reduction — what customer data backs that up?"

If scenario is "interview":
  - You are a hiring manager probing for specificity
  - Focus on: vague skill claims, unverified experience, generic answers without examples
  - Question tone: direct, pointed, "prove it"
  - Example: "You said you led the project — what specifically did you decide and what was the outcome?"

If scenario is "presentation":
  - You are an informed peer reviewing the logic
  - Focus on: methodology gaps, unsupported assertions, logical leaps, missing evidence
  - Question tone: intellectual, rigorous, "walk me through that"
  - Example: "You claimed X causes Y — did you account for confounding variables?"
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
        logger.warning("Groq returned empty payload")
        return None
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Failed to parse Groq JSON payload: %s", text[:800])
        return None


async def call_groq(
    prompt: str,
    timeout_seconds: float = 8.0,
    *,
    temperature: float = 0.3,
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
            logger.warning("Groq non-200 status: %s %s", response.status_code, response.text)
            return None
        body = response.json()
        choices = body.get("choices", [])
        if not choices:
            return None
        message = choices[0].get("message", {})
        return str(message.get("content", "")).strip() or None
    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError, ValueError) as exc:
        logger.warning("Groq call failed: %r", exc)
        return None


async def _repair_argument_payload(
    raw: str,
    question_count: int,
    timeout_seconds: float = 8.0,
) -> dict | None:
    repair_prompt = f"""
Convert the following malformed model output into valid JSON only.
Do not add markdown fences or commentary.
Return exactly this schema:
{{
  "claims": ["main claim 1", "main claim 2", "main claim 3"],
  "weakest_claim": "the specific claim with least evidence",
  "gap_explanation": "one sentence on why this claim is weak",
  "adversarial_questions": ["question 1", "question 2", "question 3"]
}}
Return at most {question_count} adversarial questions.

Malformed output:
{raw}
""".strip()

    repaired_raw = await call_groq(
        prompt=repair_prompt,
        timeout_seconds=timeout_seconds,
        temperature=0.1,
        max_output_tokens=1800,
    )
    parsed = _parse_json_payload(repaired_raw)
    if parsed:
        logger.info("Argument payload repair succeeded")
    else:
        logger.warning("Argument payload repair failed")
    return parsed


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
    raw = await call_groq(
        prompt=prompt,
        timeout_seconds=20.0,
        temperature=0.1,
        max_output_tokens=2200,
    )
    parsed = _parse_json_payload(raw)
    if not parsed:
        if raw:
            parsed = await _repair_argument_payload(raw, normalized_count, timeout_seconds=12.0)
        if not parsed:
            logger.warning("Argument extraction returned no parsed payload")
            return None

    required = {"claims", "weakest_claim", "gap_explanation"}
    if not required.issubset(parsed.keys()):
        logger.warning("Argument extraction missing required keys: %s", sorted(parsed.keys()))
        return None

    claims = parsed.get("claims")
    if not isinstance(claims, list):
        logger.warning("Argument extraction returned non-list claims: %r", type(claims).__name__)
        return None
    questions = _sanitize_questions(parsed.get("adversarial_questions"), normalized_count)
    if not questions:
        single_question = " ".join(str(parsed.get("adversarial_question", "")).split()).strip()
        if single_question:
            questions = [single_question]
    logger.info(
        "Argument extraction parsed %s claims and %s questions",
        len(claims),
        len(questions),
    )

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
    raw = await call_groq(prompt=prompt, timeout_seconds=6.0, max_output_tokens=300)
    parsed = _parse_json_payload(raw)
    if not parsed:
        logger.warning("Follow-up generation returned no parsed payload")
        return None

    if bool(parsed.get("should_followup")):
        question = str(parsed.get("followup_question", "")).strip()
        logger.info("Follow-up generation produced question: %s", bool(question))
        return question or None
    logger.info("Follow-up generation decided no follow-up was needed")
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
