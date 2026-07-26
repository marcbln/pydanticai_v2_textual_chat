from collections.abc import AsyncGenerator

from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage

from src.config import DEFAULT_LLM_MODEL, SYSTEM_PROMPT
from src.core.capabilities import stock_prices, weather

chat_agent = Agent(
    model=DEFAULT_LLM_MODEL,
    system_prompt=SYSTEM_PROMPT,
    capabilities=[weather, stock_prices],
)


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
