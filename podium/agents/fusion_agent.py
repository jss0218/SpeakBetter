from __future__ import annotations

from uagents import Model

from podium.agents.base import create_podium_agent
from podium.core.fusion import calculate_engagement, calculate_trend

fusion_agent = create_podium_agent(
    name="podium-fusion-agent",
    seed="podium_fusion_agent_seed_v1",
    port=8003,
    description="Multimodal speech-vision fusion agent",
)


class FusionInput(Model):
    session_id: str
    eye_contact_score: float
    posture_score: float = 0.5
    gesture_score: float = 0.4
    motion_score: float = 0.0
    brow_furrow: float = 0.0
    smile_score: float = 0.0
    expression: str = "neutral"
    filler_rate: float
    words_per_minute: float
    vocal_energy: float
    pause_count: int
    elapsed_seconds: float
    energy_history: list[float]
    engagement_history: list[dict]
    delivery_events: list[dict] = []
    vision_confidence: float = 1.0


class FusionOutput(Model):
    session_id: str
    engagement_score: float
    dominant_signal: str
    trend: str
    component_scores: dict


@fusion_agent.on_message(model=FusionInput)
async def handle_fusion(ctx, sender, msg: FusionInput) -> None:
    score, dominant_signal, component_scores = calculate_engagement(
        eye_contact_score=msg.eye_contact_score,
        posture_score=msg.posture_score,
        gesture_score=msg.gesture_score,
        motion_score=msg.motion_score,
        brow_furrow=msg.brow_furrow,
        smile_score=msg.smile_score,
        expression=msg.expression,
        filler_rate=msg.filler_rate,
        words_per_minute=msg.words_per_minute,
        vocal_energy=msg.vocal_energy,
        pause_count=msg.pause_count,
        elapsed_seconds=msg.elapsed_seconds,
        energy_history=msg.energy_history,
        engagement_history=msg.engagement_history,
        delivery_events=msg.delivery_events,
        vision_confidence=msg.vision_confidence,
    )
    trend = calculate_trend(msg.engagement_history + [{"score": score}])

    output = FusionOutput(
        session_id=msg.session_id,
        engagement_score=round(score, 3),
        dominant_signal=dominant_signal,
        trend=trend,
        component_scores=component_scores,
    )
    await ctx.send(sender, output)


if __name__ == "__main__":
    fusion_agent.run()
