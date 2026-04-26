from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Query, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.websockets import WebSocketDisconnect

from podium.agents.argument_agent import argument_agent
from podium.agents.audience_agent import audience_agent
from podium.agents.coach_agent import coach_agent
from podium.agents.fusion_agent import fusion_agent
from podium.agents.speech_agent import speech_agent
from podium.agents.vision_agent import vision_agent
from podium.db.mongo import connect, disconnect
from podium.session import SessionState
from podium.websocket_handler import handle_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(Path(__file__).resolve().parent / ".env")

app = FastAPI(title="Podium Backend", version="1.0.0")
BASE_DIR = Path(__file__).resolve().parent

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ACTIVE_WEBSOCKETS: set[WebSocket] = set()
SCENARIO = Literal["pitch", "interview", "presentation"]


@app.get("/")
async def root() -> dict:
    return {
        "status": "ok",
        "message": "Podium backend is running.",
        "health": "/health",
        "websocket": "/ws/{session_id}",
        "speech_test": "/speech-test",
        "docs": "/docs",
    }


@app.get("/speech-test")
async def speech_test() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "speech-test.html", media_type="text/html")


@app.on_event("startup")
async def on_startup() -> None:
    await connect()
    for agent in [
        coach_agent,
        speech_agent,
        vision_agent,
        fusion_agent,
        audience_agent,
        argument_agent,
    ]:
        logger.info("Agent ready: %s (%s)", agent.name, agent.address)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    for ws in list(ACTIVE_WEBSOCKETS):
        try:
            await ws.close(code=1001, reason="Server shutdown")
        except Exception:
            pass
    ACTIVE_WEBSOCKETS.clear()
    await disconnect()


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "agents": [
            {"name": coach_agent.name, "address": coach_agent.address},
            {"name": speech_agent.name, "address": speech_agent.address},
            {"name": vision_agent.name, "address": vision_agent.address},
            {"name": fusion_agent.name, "address": fusion_agent.address},
            {"name": audience_agent.name, "address": audience_agent.address},
            {"name": argument_agent.name, "address": argument_agent.address},
        ],
    }


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    user_id: str = Query(...),
    scenario: SCENARIO = Query("pitch"),
    target_duration: int = Query(300, ge=30, le=3600),
    audience_size: int = Query(8, ge=1, le=20),
) -> None:
    await websocket.accept()
    ACTIVE_WEBSOCKETS.add(websocket)

    session = SessionState.from_config(
        user_id=user_id,
        scenario=scenario,
        target_duration=target_duration,
        audience_size=audience_size,
    )
    session.session_id = session_id

    try:
        await handle_session(websocket=websocket, session_id=session_id, session=session)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected at endpoint for %s", session_id)
    finally:
        ACTIVE_WEBSOCKETS.discard(websocket)
