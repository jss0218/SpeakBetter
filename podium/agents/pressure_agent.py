from __future__ import annotations

from uagents import Model

from podium.agents.base import create_podium_agent
from podium.core.pressure import check_pressure_events

pressure_agent = create_podium_agent(
    name="podium-pressure-agent",
    seed="podium_pressure_agent_seed_v1",
    port=8006,
    description="Pressure escalation agent",
)


class PressureInput(Model):
    session_id: str
    engagement_score: float
    high_engagement_streak: float
    elapsed_seconds: float
    target_duration: int
    audience_size: int
    pressure_events_fired: list[str]
    avatar_states: dict[str, str]
    last_distraction_time: float


class PressureOutput(Model):
    session_id: str
    events_to_fire: list[dict]
    updated_pressure_level: int


@pressure_agent.on_message(model=PressureInput)
async def handle_pressure(ctx, sender, msg: PressureInput) -> None:
    events = check_pressure_events(
        pressure_events_fired=msg.pressure_events_fired,
        high_engagement_streak=msg.high_engagement_streak,
        elapsed_seconds=msg.elapsed_seconds,
        target_duration=msg.target_duration,
        audience_size=msg.audience_size,
        avatar_states=msg.avatar_states,
        last_distraction_time=msg.last_distraction_time,
    )

    level = 1
    event_names = list(msg.pressure_events_fired) + [event.get("event", "") for event in events]
    if any(name in {"audience_size_increase", "distraction_inject"} for name in event_names):
        level = max(level, 2)
    if any(name in {"timer_appear", "hand_raise"} for name in event_names):
        level = max(level, 3)

    output = PressureOutput(
        session_id=msg.session_id,
        events_to_fire=events,
        updated_pressure_level=level,
    )
    await ctx.send(sender, output)


if __name__ == "__main__":
    pressure_agent.run()
