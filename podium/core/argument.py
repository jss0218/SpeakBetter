from __future__ import annotations

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
  "adversarial_question": "challenging question targeting the weakest claim, under 35 words, referencing specific content from the transcript"
}}

Rules:
- Only include claims the speaker actually made
- The question must be specific to what was said, not generic
- If transcript has fewer than 80 words, return {{"claims": [], "weakest_claim": "", "gap_explanation": "", "adversarial_question": ""}}
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
        logger.warning("Failed to parse Ollama JSON payload")
        return None


async def call_ollama(prompt: str, timeout_seconds: int = 8) -> str | None:
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    model = os.getenv("GEMMA_MODEL", "gemma3")

    payload = {"model": model, "prompt": prompt, "stream": False}

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(f"{ollama_host}/api/generate", json=payload)
        if response.status_code != 200:
            logger.warning("Ollama non-200 status: %s", response.status_code)
            return None
        body = response.json()
        return body.get("response")
    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError, ValueError) as exc:
        logger.warning("Ollama call failed: %s", exc)
        return None


async def extract_claims_and_question(transcript: str, scenario: str) -> dict | None:
    prompt = CLAIM_EXTRACTION_PROMPT.format(scenario=scenario, transcript=transcript)
    raw = await call_ollama(prompt=prompt, timeout_seconds=8)
    parsed = _parse_json_payload(raw)
    if not parsed:
        return None

    required = {"claims", "weakest_claim", "gap_explanation", "adversarial_question"}
    if not required.issubset(parsed.keys()):
        return None

    claims = parsed.get("claims")
    if not isinstance(claims, list):
        return None

    return {
        "claims": [str(c).strip() for c in claims if str(c).strip()],
        "weakest_claim": str(parsed.get("weakest_claim", "")).strip(),
        "gap_explanation": str(parsed.get("gap_explanation", "")).strip(),
        "adversarial_question": str(parsed.get("adversarial_question", "")).strip(),
    }


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
    raw = await call_ollama(prompt=prompt, timeout_seconds=5)
    parsed = _parse_json_payload(raw)
    if not parsed:
        return None

    if bool(parsed.get("should_followup")):
        question = str(parsed.get("followup_question", "")).strip()
        return question or None
    return None
