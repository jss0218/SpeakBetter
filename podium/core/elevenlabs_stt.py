from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


async def transcribe_pcm_s16le_16k_mono(
    *,
    pcm_bytes: bytes,
    api_key: str,
    model_id: str = "scribe_v2",
    language_code: str | None = "eng",
    tag_audio_events: bool = False,
    diarize: bool = False,
    no_verbatim: bool = False,
    timeout_seconds: float = 15.0,
) -> str | None:
    """
    Transcribe raw PCM audio using ElevenLabs Speech-to-Text.

    The API supports a special low-latency input format:
    - 16-bit PCM, 16kHz sample rate, mono, little-endian (pcm_s16le_16)
    """
    if not api_key:
        return None
    if not pcm_bytes:
        return None

    url = "https://api.elevenlabs.io/v1/speech-to-text"
    headers = {"xi-api-key": api_key, "Accept": "application/json"}

    # ElevenLabs expects multipart/form-data with fields in the body.
    data: dict[str, Any] = {
        "model_id": model_id,
        "file_format": "pcm_s16le_16",
        "tag_audio_events": str(bool(tag_audio_events)).lower(),
        "diarize": str(bool(diarize)).lower(),
        "no_verbatim": str(bool(no_verbatim)).lower(),
    }
    if language_code is None:
        data["language_code"] = ""
    else:
        data["language_code"] = language_code

    files = {
        "file": ("audio.pcm", pcm_bytes, "application/octet-stream"),
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.post(url, headers=headers, data=data, files=files)
        if resp.status_code != 200:
            body = (resp.text or "").strip()
            logger.warning("ElevenLabs STT non-200 status: %s body=%s", resp.status_code, body[:300])
            return None
        payload = resp.json()
        text = str(payload.get("text", "")).strip()
        if not text:
            logger.info("ElevenLabs STT empty text; keys=%s", sorted(list(payload.keys()))[:30])
        return text or None
    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError) as exc:
        logger.warning("ElevenLabs STT request failed: %s", exc)
        return None
    except Exception as exc:
        logger.warning("ElevenLabs STT parse failed: %s", exc)
        return None

