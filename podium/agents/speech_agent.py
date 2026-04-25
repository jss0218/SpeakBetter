from __future__ import annotations

from uagents import Model

from podium.agents.base import create_podium_agent
from podium.core.speech import (
    calculate_filler_score,
    calculate_pace_score,
    calculate_wpm,
    count_fillers,
    normalize_amplitude,
)

speech_agent = create_podium_agent(
    name="podium-speech-agent",
    seed="podium_speech_agent_seed_v1",
    port=8001,
    description="Speech signal extraction agent",
)


class SpeechInput(Model):
    session_id: str
    transcript_chunk: str
    word_count: int
    elapsed_seconds: float
    raw_amplitude: float
    current_filler_count: int
    energy_history: list[float]


class SpeechOutput(Model):
    session_id: str
    new_fillers: int
    filler_words_found: list[str]
    filler_rate: float
    words_per_minute: float
    pause_detected: bool
    vocal_energy: float
    pace_score: float
    filler_score: float


@speech_agent.on_message(model=SpeechInput)
async def handle_speech(ctx, sender, msg: SpeechInput) -> None:
    new_fillers, filler_words = count_fillers(msg.transcript_chunk)
    total_fillers = max(0, int(msg.current_filler_count)) + new_fillers

    wpm = calculate_wpm(max(0, int(msg.word_count)), msg.elapsed_seconds)
    elapsed_minutes = max(msg.elapsed_seconds / 60.0, 1 / 60.0)
    filler_rate = total_fillers / elapsed_minutes
    vocal_energy = normalize_amplitude(msg.raw_amplitude, msg.energy_history)

    output = SpeechOutput(
        session_id=msg.session_id,
        new_fillers=new_fillers,
        filler_words_found=filler_words,
        filler_rate=round(filler_rate, 3),
        words_per_minute=round(wpm, 3),
        pause_detected=len((msg.transcript_chunk or "").strip()) == 0,
        vocal_energy=round(vocal_energy, 3),
        pace_score=round(calculate_pace_score(wpm), 3),
        filler_score=round(calculate_filler_score(filler_rate), 3),
    )
    await ctx.send(sender, output)


if __name__ == "__main__":
    speech_agent.run()
