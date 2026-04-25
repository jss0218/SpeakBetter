"""
# Podium Coach Agent

Real-time AI public speaking coach that simulates a live reactive audience,
provides live coaching while you speak, and challenges you with adversarial
questions targeting the weakest point in your argument.

## What I do
- Simulate a reactive audience (8-40 avatars) responding to your delivery
- Analyze speech patterns: filler words, pace, vocal energy, eye contact
- Coach you with specific tips referencing your actual words
- Find logical gaps in your argument using on-device AI
- Challenge you with a hard question targeting your weakest claim
- Generate a personalized breakdown with your stress signature

## When to use me
- Practicing an investor pitch
- Preparing for a job interview
- Rehearsing a conference presentation
- Improving general public speaking confidence
- Testing arguments before a debate or presentation

## How to start
Just tell me what you want to practice:
"I want to practice a 5 minute investor pitch"
"Help me prepare for a technical job interview"
"I need to practice my conference talk for 10 minutes"
"Help me practice presenting to a classroom"

## Tags
public-speaking, coaching, presentation, pitch, interview-prep,
AI-coach, real-time-feedback, argument-analysis, audience-simulation
"""

from __future__ import annotations

import os
import re
from uuid import uuid4

from uagents import Model

from podium.agents.base import create_podium_agent
from podium.core.coach import generate_realtime_tip, generate_session_breakdown, voice_tip

try:
    from uagents.experimental.chat import ChatMessage
except Exception:  # pragma: no cover
    class ChatMessage(Model):
        content: str


coach_agent = create_podium_agent(
    name="podium-coach-agent",
    seed="podium_coach_agent_seed_v1",
    port=8000,
    description="Main Podium coach agent and ASI:One entrypoint",
)


class CoachTipRequest(Model):
    session_id: str
    recent_transcript: str
    dominant_signal: str
    coach_tips: list[dict]
    last_tip_timestamp: float
    current_timestamp: float


class CoachTipResponse(Model):
    session_id: str
    tip: str
    audio_base64: str
    has_audio: bool


class BreakdownRequest(Model):
    session_id: str
    session_snapshot: dict


class BreakdownResponse(Model):
    session_id: str
    breakdown: dict


def _parse_scenario_and_duration(content: str) -> tuple[str, int]:
    text = (content or "").lower()

    scenario = "investor_pitch"
    if "interview" in text:
        scenario = "job_interview"
    elif "classroom" in text or "class" in text:
        scenario = "classroom"
    elif "conference" in text or "talk" in text:
        scenario = "conference"
    elif "pitch" in text:
        scenario = "investor_pitch"

    duration_seconds = 300
    match = re.search(r"(\d+)\s*(minute|minutes|min)", text)
    if match:
        duration_seconds = max(60, int(match.group(1)) * 60)

    return scenario, duration_seconds


@coach_agent.on_message(model=ChatMessage)
async def handle_chat(ctx, sender, msg: ChatMessage) -> None:
    scenario, duration = _parse_scenario_and_duration(getattr(msg, "content", ""))
    session_id = str(uuid4())
    response = (
        f"Ready to coach your {scenario}.\n"
        f"Session ID: {session_id}\n"
        f"Connect your browser to: ws://localhost:8000/ws/{session_id}?user_id=asi_user&scenario={scenario}&target_duration={duration}\n"
        "Start speaking when you see the audience appear.\n"
        "I will coach you live and ask you a tough question at the end."
    )
    await ctx.send(sender, ChatMessage(content=response))


@coach_agent.on_message(model=CoachTipRequest)
async def handle_tip_request(ctx, sender, msg: CoachTipRequest) -> None:
    tip = await generate_realtime_tip(
        recent_transcript=msg.recent_transcript,
        dominant_signal=msg.dominant_signal,
        coach_tips=msg.coach_tips,
        last_tip_timestamp=msg.last_tip_timestamp,
        current_timestamp=msg.current_timestamp,
    )

    audio_base64 = ""
    if tip:
        elevenlabs_key = os.getenv("ELEVENLABS_API_KEY", "")
        audio = await voice_tip(tip, elevenlabs_key)
        if audio:
            audio_base64 = audio

    output = CoachTipResponse(
        session_id=msg.session_id,
        tip=tip or "",
        audio_base64=audio_base64,
        has_audio=bool(audio_base64),
    )
    await ctx.send(sender, output)


@coach_agent.on_message(model=BreakdownRequest)
async def handle_breakdown_request(ctx, sender, msg: BreakdownRequest) -> None:
    breakdown = await generate_session_breakdown(msg.session_snapshot)
    output = BreakdownResponse(session_id=msg.session_id, breakdown=breakdown)
    await ctx.send(sender, output)


if __name__ == "__main__":
    coach_agent.run()
