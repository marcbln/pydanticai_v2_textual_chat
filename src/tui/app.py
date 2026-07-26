from typing import ClassVar

from pydantic_ai.messages import ModelMessage
from rich.markdown import Markdown
from textual.app import App, ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Footer, Header, Input, Static

from src.core.agent import AgentService


class ChatMessage(Static):
    pass


class UserMessage(ChatMessage):
    def __init__(self, content: str) -> None:
        super().__init__()
        self.content = content

    def render(self) -> str:
        return f"[bold blue]You:[/bold blue]\n{self.content}"


class AgentMessage(ChatMessage):
    def __init__(self, content: str = "") -> None:
        super().__init__()
        self.content = content

    def update_text(self, text: str) -> None:
        self.content = text
        self.update(Markdown(self.content))


class ChatApp(App[None]):
    CSS_PATH = "styles.tcss"

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+r", "clear_chat", "Reset Chat History"),
    ]

    def __init__(self, agent_service: AgentService | None = None) -> None:
        super().__init__()
        self.agent_service = agent_service or AgentService()
        self.conversation_history: list[ModelMessage] = []

    def compose(self) -> ComposeResult:
        yield Static("PydanticAI v2 - Chat Assistant", id="app-title")
        yield Header(show_clock=True)

        with VerticalScroll(id="chat-container"):
            pass

        with Vertical(id="input-container"):
            yield Input(
                placeholder="Type your message here and press Enter...", id="user-input"
            )

        yield Footer()

    async def on_mount(self) -> None:
        self.query_one(Input).focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        user_prompt = event.value.strip()
        if not user_prompt:
            return

        input_widget = self.query_one("#user-input", Input)
        input_widget.value = ""

        chat_container = self.query_one("#chat-container", VerticalScroll)

        user_msg = UserMessage(user_prompt)
        user_msg.add_class("user-message")
        await chat_container.mount(user_msg)
        user_msg.scroll_visible()

        agent_msg = AgentMessage()
        agent_msg.add_class("agent-message")
        await chat_container.mount(agent_msg)
        agent_msg.scroll_visible()

        input_widget.disabled = True

        accumulated_text = ""
        try:
            async for chunk, updated_history in self.agent_service.stream_response(
                user_prompt, self.conversation_history
            ):
                accumulated_text += chunk
                agent_msg.update_text(accumulated_text)
                chat_container.scroll_to_widget(agent_msg)

            self.conversation_history = updated_history

        except Exception as e:  # noqa: BLE001
            agent_msg.update(f"[bold red]System Error:[/bold red] {e!s}")
        finally:
            input_widget.disabled = False
            input_widget.focus()

    async def action_clear_chat(self) -> None:
        self.conversation_history.clear()
        chat_container = self.query_one("#chat-container", VerticalScroll)

        for widget in list(chat_container.children):
            await widget.remove()

        self.notify("Conversation history reset successfully!")
