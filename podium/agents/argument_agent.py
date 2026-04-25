from __future__ import annotations

import os

from pydantic import Field
from uagents import Model

from podium.agents.base import create_podium_agent
from podium.core.argument import (
    extract_claims_and_questions,
    generate_followup_question,
    synthesize_question_audio,
)

argument_agent = create_podium_agent(
    name="podium-argument-agent",
    seed="podium_argument_agent_seed_v1",
    port=8005,
    description="Argument gap detection and adversarial QA agent",
)


class ArgumentInput(Model):
    session_id: str
    transcript: str
    scenario: str
    question_count: int = 1


class ArgumentQuestion(Model):
    text: str
    audio_base64: str = ""
    has_audio: bool = False


class ArgumentOutput(Model):
    session_id: str
    claims: list[str]
    weakest_claim: str
    gap_explanation: str
    adversarial_question: str
    adversarial_questions: list[ArgumentQuestion] = Field(default_factory=list)


class FollowupInput(Model):
    session_id: str
    original_question: str
    user_answer: str
    claims: list[str]


class FollowupOutput(Model):
    session_id: str
    should_followup: bool
    followup_question: str


@argument_agent.on_message(model=ArgumentInput)
async def handle_argument(ctx, sender, msg: ArgumentInput) -> None:
    result = await extract_claims_and_questions(
        transcript=msg.transcript,
        scenario=msg.scenario,
        question_count=3,
    )
    payload = result or {
        "claims": [],
        "weakest_claim": "",
        "gap_explanation": "",
        "adversarial_question": "",
        "adversarial_questions": [],
    }
    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY", "")
    questions: list[ArgumentQuestion] = []
    for question in payload.get("adversarial_questions", []):
        audio_base64 = await synthesize_question_audio(question, elevenlabs_key)
        questions.append(
            ArgumentQuestion(
                text=question,
                audio_base64=audio_base64 or "",
                has_audio=bool(audio_base64),
            )
        )

    if not payload.get("adversarial_question") and questions:
        payload["adversarial_question"] = questions[0].text

    output = ArgumentOutput(session_id=msg.session_id, **payload)
    output.adversarial_questions = questions
    await ctx.send(sender, output)


@argument_agent.on_message(model=FollowupInput)
async def handle_followup(ctx, sender, msg: FollowupInput) -> None:
    followup = await generate_followup_question(
        original_question=msg.original_question,
        user_answer=msg.user_answer,
        claims=msg.claims,
    )
    output = FollowupOutput(
        session_id=msg.session_id,
        should_followup=bool(followup),
        followup_question=followup or "",
    )
    await ctx.send(sender, output)


if __name__ == "__main__":
    argument_agent.run()
