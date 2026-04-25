from __future__ import annotations

from uagents import Model

from podium.agents.base import create_podium_agent
from podium.core.argument import extract_claims_and_question, generate_followup_question

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


class ArgumentOutput(Model):
    session_id: str
    claims: list[str]
    weakest_claim: str
    gap_explanation: str
    adversarial_question: str


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
    result = await extract_claims_and_question(msg.transcript, msg.scenario)
    payload = result or {
        "claims": [],
        "weakest_claim": "",
        "gap_explanation": "",
        "adversarial_question": "",
    }
    output = ArgumentOutput(session_id=msg.session_id, **payload)
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
