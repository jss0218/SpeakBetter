from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import logging
import os
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from podium.core.argument import (
    extract_claims_and_question,
    generate_followup_question,
    synthesize_question_audio,
)
from podium.core.audience import calculate_avatar_states
from podium.core.coach import generate_realtime_tip, generate_session_breakdown, generate_vision_tip, voice_tip
from podium.core.elevenlabs_stt import transcribe_pcm_s16le_16k_mono
from podium.core.fusion import calculate_engagement, calculate_trend
from podium.core.speech import calculate_wpm, count_fillers, normalize_amplitude
from podium.db.mongo import save_session
from podium.schemas import (
    AudienceUpdateMessage,
    CoachTipMessage,
    ConnectedMessage,
    EngagementUpdateMessage,
    ErrorMessage,
    QAQuestionMessage,
    SessionBreakdownMessage,
    TranscriptMessage,
    VisionCalibrationMessage,
    VisionUpdateMessage,
)
from podium.session import SessionState

logger = logging.getLogger(__name__)


def _extract_pcm16_energy(chunk: bytes) -> float:
    if not chunk:
        return 0.0
    if len(chunk) < 2:
        return 0.0
    sample_count = len(chunk) // 2
    total = 0.0
    for i in range(0, sample_count * 2, 2):
        sample = int.from_bytes(chunk[i : i + 2], byteorder="little", signed=True)
        total += abs(sample) / 32768.0
    return min(1.0, total / max(1, sample_count))


async def _safe_send_json(websocket: WebSocket, payload: dict[str, Any]) -> None:
    try:
        await websocket.send_json(payload)
    except Exception as exc:
        logger.warning("WebSocket send failed: %s", exc)


async def _send_error(websocket: WebSocket, message: str, code: str) -> None:
    error = ErrorMessage(type="error", message=message, code=code)
    await _safe_send_json(websocket, error.model_dump())


async def _handle_transcript_text(session: SessionState, websocket: WebSocket, text: str) -> None:
    clean = (text or "").strip()
    if not clean:
        session.pause_detected = True
        session.pause_count += 1
        return

    session.pause_detected = False
    fillers, filler_words = count_fillers(clean)
    projected_word_count = session.word_count + len(clean.split())
    wpm = calculate_wpm(projected_word_count, session.get_elapsed_seconds())
    session.add_transcript_chunk(clean, fillers, wpm, session.vocal_energy, filler_words)
    payload = TranscriptMessage(
        type="transcript",
        text=clean,
        filler_count=session.filler_count,
        wpm=session.words_per_minute,
        pause_detected=session.pause_detected,
        timestamp=session.get_elapsed_seconds(),
    )
    await _safe_send_json(websocket, payload.model_dump())


def _cancel_live_tasks(tasks: list[asyncio.Task]) -> "asyncio.Future":
    for task in tasks:
        task.cancel()
    return asyncio.gather(*tasks, return_exceptions=True)


def _extract_incremental_delta(prev: str, current: str) -> str:
    """
    Given a growing transcript, extract the "new" portion robustly.

    ElevenLabs STT is called on overlapping rolling windows. The returned text can:
    - start mid-sentence (not from the beginning of the session)
    - change punctuation/casing in the overlap
    - slightly rewrite earlier words

    So we compute the delta by finding the largest token overlap between:
    prev suffix and current prefix.
    """
    prev_tokens = [t.lower() for t in (prev or "").split()]
    cur_tokens = [t.lower() for t in (current or "").split()]
    if not cur_tokens:
        return ""
    if not prev_tokens:
        return current.strip()

    max_k = min(len(prev_tokens), len(cur_tokens))
    overlap_k = 0
    for k in range(max_k, 0, -1):
        if prev_tokens[-k:] == cur_tokens[:k]:
            overlap_k = k
            break

    if overlap_k > 0:
        return " ".join((current or "").split()[overlap_k:]).strip()

    # Fallback: if there is no detectable overlap, only emit something when
    # the current text is clearly longer, otherwise treat as rewrite/noise.
    cur_raw_tokens = (current or "").split()
    prev_raw_tokens = (prev or "").split()
    if len(cur_raw_tokens) > len(prev_raw_tokens):
        return " ".join(cur_raw_tokens[len(prev_raw_tokens) :]).strip()
    return ""


async def handle_elevenlabs_stt_stream(
    session: SessionState,
    websocket: WebSocket,
    audio_queue: "asyncio.Queue[bytes]",
    stop_event: asyncio.Event,
) -> None:
    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY", "")
    if not elevenlabs_key:
        logger.info("ELEVENLABS_API_KEY not set; continuing with energy-only mode.")

    try:
        # Rolling PCM16 @16kHz mono buffer; we keep overlap to avoid boundary dropouts.
        pcm_buffer = bytearray()
        last_text = ""
        last_request_at = 0.0

        bytes_per_second = 16000 * 2
        min_window_s = 2.5
        request_every_s = 1.25
        window_s = 6.0
        max_buffer_s = 12.0
        recent_energy: list[float] = []

        min_bytes = int(bytes_per_second * min_window_s)
        window_bytes = int(bytes_per_second * window_s)
        max_buffer_bytes = int(bytes_per_second * max_buffer_s)

        while not stop_event.is_set():
            try:
                chunk = await asyncio.wait_for(audio_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except Exception as exc:
                logger.warning("Audio queue read failed: %s", exc)
                continue

            energy = normalize_amplitude(_extract_pcm16_energy(chunk), session.energy_history)
            session.vocal_energy = energy
            recent_energy.append(energy)
            if len(recent_energy) > 12:
                recent_energy = recent_energy[-12:]

            # Always buffer audio; STT will be skipped if key isn't set.
            if chunk:
                pcm_buffer.extend(chunk)
                if len(pcm_buffer) > max_buffer_bytes:
                    # Keep most recent audio only (rolling window).
                    pcm_buffer = pcm_buffer[-max_buffer_bytes:]

            now = session.get_elapsed_seconds()
            if now - last_request_at < request_every_s:
                continue
            if len(pcm_buffer) < min_bytes:
                continue
            if recent_energy and max(recent_energy) < 0.01:
                session.pause_detected = True
                continue
            last_request_at = now

            if not elevenlabs_key:
                session.pause_detected = False
                continue

            # Transcribe the most recent window (overlap improves completeness).
            payload_bytes = bytes(pcm_buffer[-window_bytes:]) if len(pcm_buffer) > window_bytes else bytes(pcm_buffer)

            text = await transcribe_pcm_s16le_16k_mono(
                pcm_bytes=payload_bytes,
                api_key=elevenlabs_key,
                model_id=os.getenv("ELEVENLABS_STT_MODEL_ID", "scribe_v2"),
                language_code="eng",
                tag_audio_events=False,
                diarize=False,
                no_verbatim=False,  # IMPORTANT: keep filler words like "um"/"uh"
                timeout_seconds=8.0,
            )
            if not text:
                continue

            # Extract incremental delta from overlapping windows.
            delta = _extract_incremental_delta(last_text, text)
            last_text = text
            if not delta:
                continue

            await _handle_transcript_text(session, websocket, delta)
    finally:
        return


async def handle_vision_update(msg: dict, session: SessionState) -> None:
    try:
        parsed = VisionUpdateMessage(**msg)
    except Exception:
        return
    session.update_vision(
        eye_contact=parsed.eye_contact,
        face_detected=parsed.face_detected,
        gesture=parsed.gesture_detected,
        posture_score=parsed.posture_score,
        motion_score=parsed.motion_score,
        brow_furrow=parsed.brow_furrow,
        smile_score=parsed.smile_score,
        expression=parsed.expression,
        head_yaw=parsed.head_yaw,
        head_pitch=parsed.head_pitch,
        head_roll=parsed.head_roll,
        face_size=parsed.face_size,
        hand_motion=parsed.hand_motion,
        vision_confidence=parsed.vision_confidence,
    )


async def handle_vision_calibration(msg: dict, session: SessionState) -> None:
    try:
        parsed = VisionCalibrationMessage(**msg)
    except Exception:
        return
    session.update_vision_calibration(parsed.samples)


async def audience_update(session: SessionState, websocket: WebSocket) -> None:
    new_states, delays = calculate_avatar_states(
        engagement_score=session.engagement_score,
        dominant_signal=session.dominant_signal,
        current_states=session.avatar_states,
        stubbornness_factors=session.avatar_stubbornness,
        audience_size=session.audience_size,
    )
    session.avatar_states = new_states

    payload = AudienceUpdateMessage(
        type="audience_update",
        avatar_states=new_states,
        transition_delays_ms=delays,
    )
    await _safe_send_json(websocket, payload.model_dump())


async def fusion_loop(session: SessionState, websocket: WebSocket, stop_event: asyncio.Event) -> None:
    while not stop_event.is_set() and session.ended_at is None:
        try:
            score, dominant_signal, components = calculate_engagement(
                eye_contact_score=session.eye_contact_score,
                posture_score=session.posture_score,
                gesture_score=session.gesture_score,
                motion_score=session.motion_score,
                brow_furrow=session.brow_furrow,
                smile_score=session.smile_score,
                expression=session.expression,
                filler_rate=session.filler_rate,
                words_per_minute=session.words_per_minute,
                vocal_energy=session.vocal_energy,
                pause_count=session.pause_count,
                elapsed_seconds=session.get_elapsed_seconds(),
                energy_history=session.energy_history,
                engagement_history=session.engagement_history,
                delivery_events=session.delivery_events,
                vision_confidence=session.vision_confidence,
            )
            trend = calculate_trend(session.engagement_history + [{"score": score}])
            session.update_engagement(score=score, signal=dominant_signal, trend=trend)

            payload = EngagementUpdateMessage(
                type="engagement_update",
                score=session.engagement_score,
                dominant_signal=dominant_signal,
                trend=trend,
                component_scores=components,
            )
            await _safe_send_json(websocket, payload.model_dump())
            await audience_update(session, websocket)
        except Exception as exc:
            logger.exception("fusion_loop failed: %s", exc)

        await asyncio.sleep(2)


async def coach_loop(session: SessionState, websocket: WebSocket, stop_event: asyncio.Event) -> None:
    while not stop_event.is_set() and session.ended_at is None:
        try:
            if session.session_phase != "speaking":
                await asyncio.sleep(2)
                continue
            now = session.get_elapsed_seconds()
            tip = await generate_realtime_tip(
                recent_transcript=session.get_recent_transcript(30),
                dominant_signal=session.dominant_signal,
                coach_tips=session.coach_tips,
                last_tip_timestamp=session.last_tip_timestamp,
                current_timestamp=now,
            )
            if tip:
                session.coach_tips.append({"tip": tip, "timestamp": now})
                session.last_tip_timestamp = now
                audio_base64 = None
                elevenlabs_key = os.getenv("ELEVENLABS_API_KEY", "")
                if elevenlabs_key:
                    audio_base64 = await voice_tip(tip, elevenlabs_key)
                payload = CoachTipMessage(type="coach_tip", tip=tip, audio_base64=audio_base64)
                await _safe_send_json(websocket, payload.model_dump())
        except Exception as exc:
            logger.exception("coach_loop failed: %s", exc)

        await asyncio.sleep(30)


async def vision_coach_loop(session: SessionState, websocket: WebSocket, stop_event: asyncio.Event) -> None:
    while not stop_event.is_set() and session.ended_at is None:
        try:
            if session.session_phase != "speaking":
                await asyncio.sleep(2)
                continue
            now = session.get_elapsed_seconds()
            if now - float(session.last_tip_timestamp) >= 12:
                tip, signal = generate_vision_tip(
                    recent_vision=session.get_recent_vision(10),
                    last_signal=session.last_vision_tip_signal,
                    delivery_events=session.delivery_events,
                    vision_confidence=session.vision_confidence,
                )
                session.last_vision_tip_signal = signal
                if tip:
                    session.coach_tips.append({"tip": tip, "timestamp": now, "source": "vision"})
                    session.last_tip_timestamp = now
                    payload = CoachTipMessage(type="coach_tip", tip=tip, audio_base64=None)
                    await _safe_send_json(websocket, payload.model_dump())
        except Exception as exc:
            logger.exception("vision_coach_loop failed: %s", exc)

        await asyncio.sleep(2)


async def argument_loop(session: SessionState, websocket: WebSocket, stop_event: asyncio.Event) -> None:
    del websocket
    while not stop_event.is_set() and session.ended_at is None:
        try:
            if session.session_phase != "speaking":
                await asyncio.sleep(2)
                continue
            if session.word_count >= 100:
                result = await extract_claims_and_question(session.full_transcript, session.scenario)
                if result:
                    session.claims = result.get("claims", [])
                    session.weakest_claim = result.get("weakest_claim", "")
                    session.gap_explanation = result.get("gap_explanation", "")
                    session.adversarial_question = result.get("adversarial_question", "")
        except Exception as exc:
            logger.exception("argument_loop failed: %s", exc)

        await asyncio.sleep(45)


async def _finalize_session(
    session: SessionState,
    websocket: WebSocket,
    stop_event: asyncio.Event,
) -> None:
    session.session_phase = "finalizing"
    session.ended_at = session.ended_at or datetime.now(timezone.utc)
    snapshot = session.to_mongo()
    snapshot["elapsed_seconds"] = session.get_elapsed_seconds()
    breakdown = await generate_session_breakdown(snapshot)
    session.final_breakdown = breakdown

    breakdown_msg = SessionBreakdownMessage(
        type="session_breakdown",
        breakdown=breakdown,
        engagement_history=session.engagement_history,
    )
    await _safe_send_json(websocket, breakdown_msg.model_dump())

    stop_event.set()
    await save_session(session.to_mongo())

    try:
        await websocket.close(code=1000, reason="Session complete")
    except Exception:
        pass


async def handle_pause_session(
    session: SessionState,
    websocket: WebSocket,
    tasks: list[asyncio.Task],
    stop_event: asyncio.Event,
) -> None:
    session.session_phase = "asking_question"

    def _clean_question(text: str) -> str:
        q = " ".join(str(text or "").split()).strip()
        if not q:
            return ""
        # Remove stray quoting/backticks that sometimes leak from models.
        q = q.strip("`\"' ").strip()
        # Keep it reasonably short for TTS and UI.
        if len(q) > 220:
            q = q[:219].rstrip() + "…"
        # Normalize punctuation; ensure it's a question.
        if not q.endswith("?"):
            q = q.rstrip(".! ") + "?"
        return q

    def _looks_valid_question(text: str) -> bool:
        q = _clean_question(text)
        if not q:
            return False
        # Must contain enough words to be meaningful, but not be a paragraph.
        words = [w for w in q.replace("…", "").split() if w.strip()]
        if len(words) < 6 or len(words) > 45:
            return False
        # Avoid obvious garbage / placeholder-y output.
        low = q.lower()
        if any(tok in low for tok in ["lorem", "asdf", "qwerty", "null", "undefined", "{", "}", "[", "]"]):
            return False
        # Must have mostly printable characters.
        printable = sum(1 for ch in q if ch.isprintable())
        if printable / max(1, len(q)) < 0.98:
            return False
        # Avoid too much repeated punctuation.
        if "??" in q or "!!" in q:
            return False
        return True

    def _fallback_crowd_question(transcript: str, scenario: str) -> str:
        # Used when the claim extractor can't produce a question (API missing/timeout/etc).
        # Keep it specific by referencing a short snippet, without dev-y phrasing.
        words = [w for w in (transcript or "").split() if w.strip()]
        tail = " ".join(words[-14:]).strip()
        if scenario == "pitch":
            base = "What specific proof do you have that customers will pay for this?"
        elif scenario == "interview":
            base = "Can you give one concrete example from your experience that proves your main point?"
        else:  # presentation
            base = "What evidence supports your main claim, and what would change your conclusion?"
        if tail:
            return f'{base} For example, you mentioned: "{tail}".'
        return base

    # Try to generate a crowd question.
    # The extractor may return empty for short/low-substance transcripts; we always fall back.
    if not session.adversarial_question.strip():
        try:
            result = await extract_claims_and_question(session.full_transcript, session.scenario)
            if result:
                session.claims = result.get("claims", [])
                session.weakest_claim = result.get("weakest_claim", "")
                session.gap_explanation = result.get("gap_explanation", "")
                session.adversarial_question = result.get("adversarial_question", "")
                logger.info(
                    "Pause-session argument generation completed: claims=%s question=%s",
                    len(session.claims),
                    bool(session.adversarial_question.strip()),
                )
            else:
                logger.warning("Pause-session argument generation returned no result")
        except Exception as exc:
            logger.exception("Pause-session argument generation failed: %s", exc)

    # Always ask *something* on pause, even for very short transcripts.
    if not session.adversarial_question.strip():
        session.adversarial_question = _fallback_crowd_question(session.full_transcript, session.scenario)

    question = _clean_question(session.adversarial_question)
    if not _looks_valid_question(question):
        question = _clean_question(_fallback_crowd_question(session.full_transcript, session.scenario))
    if not question:
        logger.warning(
            "Skipping QA question send because adversarial_question is empty. word_count=%s",
            session.word_count,
        )
        # Extremely defensive fallback; should be unreachable.
        question = "What is the single main point you want the audience to remember?"

    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY", "")
    audio_base64 = await synthesize_question_audio(question, elevenlabs_key)
    session.qa_answer_transcript = ""
    session.user_qa_answer = ""
    session.qa_question_count += 1
    qa_msg = QAQuestionMessage(type="qa_question", question=question, audio_base64=audio_base64)
    await _safe_send_json(websocket, qa_msg.model_dump())


async def handle_qa_answer_done(
    session: SessionState,
    websocket: WebSocket,
    tasks: list[asyncio.Task],
    stop_event: asyncio.Event,
) -> None:
    session.session_phase = "qa_complete"
    spoken_answer = session.qa_answer_transcript.strip()
    if spoken_answer:
        session.user_qa_answer = spoken_answer

    await _cancel_live_tasks(tasks)
    await _finalize_session(session, websocket, stop_event)


async def handle_session(websocket: WebSocket, session_id: str, session: SessionState) -> None:
    del session_id

    stop_event = asyncio.Event()
    audio_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=64)

    connected = ConnectedMessage(type="connected", session_id=session.session_id, config=session.get_snapshot())
    await _safe_send_json(websocket, connected.model_dump())

    stt_task = asyncio.create_task(handle_elevenlabs_stt_stream(session, websocket, audio_queue, stop_event))
    tasks = [
        asyncio.create_task(fusion_loop(session, websocket, stop_event)),
        asyncio.create_task(coach_loop(session, websocket, stop_event)),
        asyncio.create_task(vision_coach_loop(session, websocket, stop_event)),
        asyncio.create_task(argument_loop(session, websocket, stop_event)),
    ]

    try:
        while not stop_event.is_set():
            packet = await websocket.receive()

            if packet.get("type") == "websocket.disconnect":
                raise WebSocketDisconnect()

            if packet.get("bytes") is not None:
                try:
                    audio_queue.put_nowait(packet["bytes"])
                except asyncio.QueueFull:
                    pass
                continue

            text = packet.get("text")
            if not text:
                continue

            try:
                msg = json.loads(text)
            except json.JSONDecodeError:
                await _send_error(websocket, "Invalid JSON payload", "bad_json")
                continue

            msg_type = msg.get("type")
            if msg_type == "vision_update":
                await handle_vision_update(msg, session)
            elif msg_type == "vision_calibration":
                await handle_vision_calibration(msg, session)
            elif msg_type == "pause_session":
                await handle_pause_session(session, websocket, tasks, stop_event)
                if stop_event.is_set():
                    break
            elif msg_type == "session_end":
                await _cancel_live_tasks(tasks)
                await _finalize_session(session, websocket, stop_event)
                break
            elif msg_type == "qa_answer_done":
                await handle_qa_answer_done(session, websocket, tasks, stop_event)
                break
            elif msg_type == "qa_answer":
                answer = str(msg.get("answer", "")).strip()
                if answer:
                    session.user_qa_answer = answer
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for session %s", session.session_id)
    except Exception as exc:
        logger.exception("Session handler failed: %s", exc)
        await _send_error(websocket, "Internal session error", "internal_error")
    finally:
        stop_event.set()
        for task in tasks:
            task.cancel()
        stt_task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.gather(stt_task, return_exceptions=True)
        session.ended_at = session.ended_at or datetime.now(timezone.utc)
        await save_session(session.to_mongo())
