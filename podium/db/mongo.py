from __future__ import annotations

from datetime import datetime, timezone
import logging
import os

import motor.motor_asyncio
from pymongo import ASCENDING, DESCENDING

logger = logging.getLogger(__name__)

client: motor.motor_asyncio.AsyncIOMotorClient | None = None
db = None


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def connect() -> None:
    global client, db
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_DB", "podium")

    client = motor.motor_asyncio.AsyncIOMotorClient(uri, serverSelectionTimeoutMS=3000)
    db = client[db_name]

    try:
        await client.admin.command("ping")
        await db.sessions.create_index([("user_id", ASCENDING)])
        await db.sessions.create_index([("started_at", DESCENDING)])
        await db.users.create_index([("user_id", ASCENDING)], unique=True)
        logger.info("MongoDB connected: %s", db_name)
    except Exception as exc:
        logger.warning("MongoDB unavailable; running without persistence: %s", exc)
        if client is not None:
            client.close()
        client = None
        db = None


async def disconnect() -> None:
    global client, db
    if client is not None:
        client.close()
    client = None
    db = None


async def save_session(session_data: dict) -> None:
    if db is None:
        logger.warning("MongoDB not connected; skipping save_session")
        return
    session_id = session_data.get("session_id")
    if not session_id:
        logger.warning("Session data missing session_id; skipping save_session")
        return
    await db.sessions.update_one(
        {"session_id": session_id},
        {"$set": session_data, "$setOnInsert": {"created_at": _utc_iso_now()}},
        upsert=True,
    )


async def get_user_sessions(user_id: str, limit: int = 10) -> list[dict]:
    if db is None:
        return []
    cursor = (
        db.sessions.find({"user_id": user_id})
        .sort("started_at", DESCENDING)
        .limit(max(1, int(limit)))
    )
    return await cursor.to_list(length=max(1, int(limit)))


async def get_user(user_id: str) -> dict | None:
    if db is None:
        return None
    return await db.users.find_one({"user_id": user_id})


async def upsert_user(user_id: str, session_data: dict) -> None:
    if db is None:
        return

    current = await get_user(user_id)
    current_count = int((current or {}).get("sessions_completed", 0))
    current_avg = float((current or {}).get("avg_engagement_baseline", 0.0))
    new_engagement = float(session_data.get("engagement_score", 0.0))

    next_count = current_count + 1
    next_avg = ((current_avg * current_count) + new_engagement) / max(1, next_count)

    await db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "avg_engagement_baseline": round(next_avg, 4),
                "last_session": _utc_iso_now(),
                "last_scenario": session_data.get("scenario", ""),
            },
            "$inc": {"sessions_completed": 1},
            "$setOnInsert": {"created_at": _utc_iso_now()},
        },
        upsert=True,
    )


async def update_stress_signature(user_id: str, new_session: dict) -> None:
    if db is None:
        return

    recent = await (
        db.sessions.find({"user_id": user_id})
        .sort("started_at", DESCENDING)
        .limit(3)
        .to_list(length=3)
    )

    sessions = [new_session] + recent
    if len(sessions) < 3:
        return

    patterns: list[str] = []

    filler_rates = [float(s.get("filler_rate", 0.0)) for s in sessions[:3]]
    if min(filler_rates) > 4.0:
        patterns.append("filler_rate_remains_high")

    eye_drop_correlation_hits = 0
    for sess in sessions[:3]:
        history = sess.get("engagement_history", [])
        if len(history) < 4:
            continue
        scores = [float(item.get("score", 0.0)) for item in history if isinstance(item, dict)]
        if not scores:
            continue
        if max(scores) - min(scores) > 0.2 and float(sess.get("eye_contact_score", 0.0)) < 0.6:
            eye_drop_correlation_hits += 1
    if eye_drop_correlation_hits >= 2:
        patterns.append("eye_contact_drop_correlates_with_engagement_drop")

    if not patterns:
        patterns.append("no_stable_stress_pattern_detected_yet")

    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"stress_signature": patterns, "stress_signature_updated_at": _utc_iso_now()}},
        upsert=True,
    )
