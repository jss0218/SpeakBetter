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
- Practicing a pitch
- Preparing for an interview
- Rehearsing a presentation
- Improving general public speaking confidence
- Testing arguments before a debate or presentation

## How to start
Just tell me what you want to practice or ask for coaching advice:
"How do I improve my eye contact?"
"What are the most common filler words to avoid?"
"Give me tips for a 5-minute pitch"

## Tags
public-speaking, coaching, presentation, pitch, interview-prep,
AI-coach, real-time-feedback, argument-analysis, audience-simulation
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import os

from openai import OpenAI
from uagents import Agent, Context, Model, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)

client = OpenAI(
    base_url="https://api.asi1.ai/v1",
    api_key=os.getenv("ASI1_API_KEY", ""),
)

coach_agent = Agent(
    name="podium-coach-agent",
    seed="podium_coach_agent_seed_v12026",
    port=8000,
    mailbox=True,
    publish_agent_details=True,
)

protocol = Protocol(spec=chat_protocol_spec)


@protocol.on_message(ChatMessage)
async def handle_message(ctx: Context, sender: str, msg: ChatMessage) -> None:
    await ctx.send(
        sender,
        ChatAcknowledgement(timestamp=datetime.now(), acknowledged_msg_id=msg.msg_id),
    )

    text = ""
    for item in msg.content:
        if isinstance(item, TextContent):
            text += item.text

    response = "I am afraid something went wrong and I am unable to answer your question at the moment."
    try:
        r = client.chat.completions.create(
            model="asi1",
            messages=[
                {
                    "role": "system",
                    "content": """You are Podium, an expert AI public speaking coach.
You help users improve their public speaking skills: delivery, eye contact, pacing, filler words,
posture, gestures, argument structure, and confidence.
Give specific, actionable advice. Keep responses concise (under 150 words).
If asked about something unrelated to public speaking or coaching, politely redirect.""",
                },
                {"role": "user", "content": text},
            ],
            max_tokens=2048,
        )
        response = str(r.choices[0].message.content)
    except Exception:
        ctx.logger.exception("Error querying ASI:One model")

    await ctx.send(
        sender,
        ChatMessage(
            timestamp=datetime.utcnow(),
            msg_id=uuid4(),
            content=[
                TextContent(type="text", text=response),
                EndSessionContent(type="end-session"),
            ],
        ),
    )


@protocol.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement) -> None:
    pass


coach_agent.include(protocol, publish_manifest=True)


SYSTEM_PROMPT = """You are Podium, an expert AI public speaking coach.
You help users improve their public speaking skills: delivery, eye contact, pacing, filler words,
posture, gestures, argument structure, and confidence.
Give specific, actionable advice. Keep responses concise (under 150 words).
If asked about something unrelated to public speaking or coaching, politely redirect."""


class CoachRequest(Model):
    question: str


class CoachResponse(Model):
    timestamp: int
    answer: str
    agent_address: str


@coach_agent.on_rest_get("/rest/get", CoachResponse)
async def handle_get(ctx: Context) -> Dict[str, Any]:
    return {
        "timestamp": int(time.time()),
        "answer": "Podium coach agent is live. POST a question to /rest/post to get coaching advice.",
        "agent_address": ctx.agent.address,
    }


@coach_agent.on_rest_post("/rest/post", CoachRequest, CoachResponse)
async def handle_post(ctx: Context, req: CoachRequest) -> CoachResponse:
    answer = "I am afraid something went wrong and I am unable to answer your question at the moment."
    try:
        r = client.chat.completions.create(
            model="asi1",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": req.question},
            ],
            max_tokens=512,
        )
        answer = str(r.choices[0].message.content)
    except Exception:
        ctx.logger.exception("Error querying ASI:One model (REST)")
    return CoachResponse(
        timestamp=int(time.time()),
        answer=answer,
        agent_address=ctx.agent.address,
    )


if __name__ == "__main__":
    coach_agent.run()
