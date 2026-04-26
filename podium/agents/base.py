from __future__ import annotations

import asyncio

from uagents import Agent
from uagents.setup import fund_agent_if_low


def create_podium_agent(
    name: str,
    seed: str,
    port: int,
    description: str = "",
) -> Agent:
    del description

    try:
        loop = asyncio.get_event_loop_policy().get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    agent = Agent(
        name=name,
        seed=seed,
        port=port,
        mailbox=True,
        publish_agent_details=True,
        loop=loop,
    )

    @agent.on_event("startup")
    async def _on_startup(ctx) -> None:
        ctx.logger.info("%s started at address %s", name, agent.address)
        try:
            fund_agent_if_low(agent.wallet.address())
        except Exception as exc:  # pragma: no cover
            ctx.logger.warning("Funding check failed for %s: %s", name, exc)

    return agent
