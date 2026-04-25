from __future__ import annotations

from uagents import Model

from podium.agents.base import create_podium_agent
from podium.core.audience import calculate_avatar_states

audience_agent = create_podium_agent(
    name="podium-audience-agent",
    seed="podium_audience_agent_seed_v1",
    port=8004,
    description="Audience behavior simulation agent",
)


class AudienceInput(Model):
    session_id: str
    engagement_score: float
    dominant_signal: str
    current_states: dict[str, str]
    stubbornness_factors: dict[str, float]
    audience_size: int


class AudienceOutput(Model):
    session_id: str
    avatar_states: dict[str, str]
    transition_delays_ms: dict[str, int]
    changed_count: int


@audience_agent.on_message(model=AudienceInput)
async def handle_audience(ctx, sender, msg: AudienceInput) -> None:
    new_states, delays = calculate_avatar_states(
        engagement_score=msg.engagement_score,
        dominant_signal=msg.dominant_signal,
        current_states=msg.current_states,
        stubbornness_factors=msg.stubbornness_factors,
        audience_size=msg.audience_size,
    )

    output = AudienceOutput(
        session_id=msg.session_id,
        avatar_states=new_states,
        transition_delays_ms=delays,
        changed_count=len(delays),
    )
    await ctx.send(sender, output)


if __name__ == "__main__":
    audience_agent.run()
