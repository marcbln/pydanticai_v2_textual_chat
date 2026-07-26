from collections import defaultdict
from typing import ClassVar

from pydantic_ai.messages import BaseToolCallPart, ModelMessage
from rich.markdown import Markdown
from rich.table import Table
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Header, Input, Static

from src.core.agent import AgentService, chat_agent


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


class CapabilitiesSidebar(VerticalScroll):
    def __init__(self, tool_to_cap: dict[str, str], capabilities: list[dict]) -> None:
        super().__init__(id="sidebar")
        self._tool_to_cap = tool_to_cap
        self._capabilities = capabilities
        self._usage: dict[str, int] = defaultdict(int)

    def compose(self) -> ComposeResult:
        yield Static("[bold]Capabilities[/bold]", id="sidebar-title")
        yield Static(id="sidebar-content")

    def on_mount(self) -> None:
        self._refresh()

    def refresh_from_history(self, history: list[ModelMessage]) -> None:
        self._usage.clear()
        for msg in history:
            parts = msg.parts if hasattr(msg, "parts") else ()
            for part in parts:
                if isinstance(part, BaseToolCallPart):
                    cap_id = self._tool_to_cap.get(part.tool_name)
                    if cap_id:
                        self._usage[cap_id] += 1
        self._refresh()

    def reset(self) -> None:
        self._usage.clear()
        self._refresh()

    def _refresh(self) -> None:
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column(ratio=0, no_wrap=True)
        table.add_column(ratio=1)
        table.add_column(ratio=0, justify="right", no_wrap=True)
        for cap in self._capabilities:
            cap_id = cap["id"]
            count = self._usage.get(cap_id, 0)
            count_str = f"[bold $success]{count}[/bold $success]" if count else "[dim]0[/dim]"
            table.add_row("●", cap_id.replace("_", " ").title(), count_str)
        content = self.query_one("#sidebar-content", Static)
        content.update(table)


class ChatApp(App[None]):
    CSS_PATH = "styles.tcss"

    BINDINGS: ClassVar = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+r", "clear_chat", "Reset Chat History"),
        ("ctrl+s", "toggle_sidebar", "Capabilities"),
    ]

    def __init__(self, agent_service: AgentService | None = None) -> None:
        super().__init__()
        self.agent_service = agent_service or AgentService()
        self.conversation_history: list[ModelMessage] = []
        self.tool_to_cap, self.capabilities_info = self._extract_capabilities()

    @staticmethod
    def _extract_capabilities() -> tuple[dict[str, str], list[dict]]:
        tool_to_cap: dict[str, str] = {}
        capabilities: list[dict] = []
        for cap in chat_agent.root_capability.capabilities:
            if cap.id is None:
                continue
            cap_type = type(cap).__name__
            if cap_type == "Capability":
                toolset = getattr(cap, "_function_toolset", None)
                tool_names = list(toolset.tools.keys()) if toolset else []
                for tn in tool_names:
                    tool_to_cap[tn] = cap.id
                tool_to_cap[cap.id] = cap.id
                capabilities.append({
                    "id": cap.id,
                    "desc": cap.description,
                    "tool_names": tool_names,
                })
            elif hasattr(cap, "native"):
                tn = cap.native.kind
                tool_to_cap[tn] = cap.id
                tool_to_cap[cap.id] = cap.id
                capabilities.append({
                    "id": cap.id,
                    "desc": cap.description,
                    "tool_names": [tn],
                })
        return tool_to_cap, capabilities

    def compose(self) -> ComposeResult:
        yield Static("PydanticAI v2 - Chat Assistant", id="app-title")
        yield Header(show_clock=True)

        with Horizontal(id="main-container"):
            yield CapabilitiesSidebar(self.tool_to_cap, self.capabilities_info)
            with VerticalScroll(id="chat-container"):
                pass

        with Vertical(id="input-container"):
            yield Input(
                placeholder="Type your message here and press Enter...", id="user-input"
            )

        yield Footer()

    async def on_mount(self) -> None:
        self.query_one(Input).focus()

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar", VerticalScroll)
        sidebar.display = not sidebar.display

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
            sidebar = self.query_one(CapabilitiesSidebar)
            sidebar.refresh_from_history(self.conversation_history)
            input_widget.disabled = False
            input_widget.focus()

    async def action_clear_chat(self) -> None:
        self.conversation_history.clear()
        chat_container = self.query_one("#chat-container", VerticalScroll)

        for widget in list(chat_container.children):
            await widget.remove()

        sidebar = self.query_one(CapabilitiesSidebar)
        sidebar.reset()
        self.notify("Conversation history reset successfully!")
