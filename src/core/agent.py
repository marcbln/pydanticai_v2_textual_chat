from collections.abc import AsyncGenerator

import httpx
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessage

from src.config import DEFAULT_LLM_MODEL, SYSTEM_PROMPT


async def get_weather(location: str) -> str:
    """Get the current weather for a given location."""
    url = f"https://wttr.in/{location}?format=%C+%t+%w+%h"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
        return f"Weather in {location}: {resp.text.strip()}"


chat_agent = Agent(
    model=DEFAULT_LLM_MODEL,
    system_prompt=SYSTEM_PROMPT,
)


@chat_agent.tool
async def weather(ctx: RunContext[None], location: str) -> str:
    """Get the current weather for a given location.

    Args:
        location: The city or region to get weather for.
    """
    return await get_weather(location)


class AgentService:
    def __init__(self, agent: Agent[None, str] = chat_agent) -> None:
        self._agent = agent

    async def stream_response(
        self,
        prompt: str,
        history: list[ModelMessage],
    ) -> AsyncGenerator[tuple[str, list[ModelMessage]]]:
        async with self._agent.run_stream(prompt, message_history=history) as result:
            async for text_chunk in result.stream_text(delta=True):
                yield text_chunk, result.all_messages()
