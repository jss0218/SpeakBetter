from __future__ import annotations

from uagents import Model

from podium.agents.base import create_podium_agent
from podium.core.vision import calculate_gesture_score, update_eye_contact_ema

vision_agent = create_podium_agent(
    name="podium-vision-agent",
    seed="podium_vision_agent_seed_v1",
    port=8002,
    description="Vision signal processing agent",
)


class VisionInput(Model):
    session_id: str
    eye_contact_raw: float
    face_detected: bool
    gesture_detected: bool
    current_ema: float
    gesture_history: list[bool]


class VisionOutput(Model):
    session_id: str
    eye_contact_score: float
    gesture_score: float
    face_detected: bool


@vision_agent.on_message(model=VisionInput)
async def handle_vision(ctx, sender, msg: VisionInput) -> None:
    eye_contact = update_eye_contact_ema(msg.current_ema, msg.eye_contact_raw)
    history = list(msg.gesture_history) + [bool(msg.gesture_detected)]
    gesture_score = calculate_gesture_score(history)

    output = VisionOutput(
        session_id=msg.session_id,
        eye_contact_score=round(eye_contact, 3),
        gesture_score=round(gesture_score, 3),
        face_detected=msg.face_detected,
    )
    await ctx.send(sender, output)


if __name__ == "__main__":
    vision_agent.run()
