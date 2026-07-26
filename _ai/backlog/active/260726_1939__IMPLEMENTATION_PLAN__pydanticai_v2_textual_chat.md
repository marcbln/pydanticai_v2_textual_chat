---
filename: "_ai/backlog/active/260726_1939__IMPLEMENTATION_PLAN__pydanticai_v2_textual_chat.md"
title: "Implement Textual Chat Interface powered by PydanticAI v2"
createdAt: 2026-07-26 19:39
updatedAt: 2026-07-26 19:39
status: draft
priority: high
tags: [python, textual, tui, pydantic-ai, llm]
estimatedComplexity: moderate
documentType: IMPLEMENTATION_PLAN
---

## 1. Problem Description
We need to provide an interactive, high-fidelity, and terminal-native chat experience for users of our Python-based AI application. Traditional CLI-based chat loops (standard input/output lines) suffer from formatting limitations, lack scrolling histories, and cannot easily display multi-column layouts or live markdown updates without causing severe terminal screen jitter. 

Our application is built on **PydanticAI v2**, which features asynchronous streaming capabilities. We need a terminal user interface (TUI) that can smoothly capture user input, display beautiful markdown rendering of code, lists, and headers, and stream real-time tokens dynamically into the visual display without blocking the main event loops.

## 2. Executive Summary
This implementation plan builds a pure Python-native Terminal User Interface (TUI) using **Textual** linked to **PydanticAI v2**. 

By adhering to **SOLID principles**, the solution decomposes concerns into highly cohesive components:
- **`src/config.py`** houses system-wide configurations, model selections, and CLI contexts.
- **`src/core/agent.py`** encapsulates LLM integration and manages conversation state via PydanticAI's `ModelMessage` history, isolated completely from any TUI rendering details.
- **`src/tui/app.py`** and **`src/tui/styles.tcss`** implement a fully asynchronous, responsive user interface utilizing custom rendering widgets. This frontend consumes text streams from our agent layer and formats them in real time using Textual's markdown rendering support.
- **`src/cli.py`** provides a Typer CLI entrypoint to easily launch the TUI or handle configuration inputs.

This design gives us a stable, asynchronous, and robust architecture that runs natively inside any standard terminal environment.

## 3. Project Environment Details
- **Project Name**: Python Project
- **Frontend root**: `frontend` (not applicable for this native TUI, but kept for context)
- **Backend root**: `src`

---

## 4. SOLID Principles Alignment
To ensure a maintainable and scalable codebase, the following design decisions are enforced:
1. **Single Responsibility Principle (SRP)**:
   - `src/core/agent.py` holds the exclusive responsibility of executing prompts through the PydanticAI model and managing history structures.
   - `src/tui/app.py` holds the exclusive responsibility of drawing widgets, reading keystrokes, and handling terminal visual rendering.
   - User inputs and Agent outputs are represented as isolated, self-rendering widgets (`UserMessage` and `AgentMessage`).
2. **Open/Closed Principle (OCP)**:
   - The TUI receives generic message objects or raw text streams. We can switch LLM engines, inject tools/dependencies into PydanticAI, or add guardrails in `core/agent.py` without modifying the rendering logic in `tui/app.py`.
3. **Liskov Substitution Principle (LSP)**:
   - Different message widgets inherit from a common `ChatMessage` base widget, ensuring they can be mounted, updated, and styled uniformly in the UI grid.
4. **Interface Segregation Principle (ISP)**:
   - The PydanticAI agent exposes plain text generators and standard message lists. It has no awareness of, or dependencies on, Textual classes (`Widget`, `Static`, `App`).
5. **Dependency Inversion Principle (DIP)**:
   - The TUI app depends on PydanticAI's clean async streaming interfaces (`StreamedRunResult.stream_text()`) rather than hardcoding low-level HTTP network calls or client client instances.

---

## 5. Phased Implementation Steps

### Phase 1: Environment Setup & Dependency Configuration
Ensure our toolchain is up-to-date and all dependencies are registered. We will use `uv` as our environment and package manager, modifying `pyproject.toml`.

```toml
# [MODIFY] pyproject.toml
# Ensure textual, pydantic-ai, typer, and rich are declared as core project dependencies.
```

**Step 1.1: Install Dependencies**
Execute the following shell commands to install the required libraries:
```bash
uv add textual pydantic-ai typer rich python-dotenv pyyaml
uv add --dev pytest pytest-asyncio black mypy ruff
```

---

### Phase 2: System Configuration & Agent Core Implementation
We will create the configuration handling and define the PydanticAI v2 Agent interface. 

```python
# [NEW FILE] src/config.py
"""System-wide configuration and environment variable loading."""

import os
from typing import Any
from dotenv import load_dotenv

# Load environment variables from a .env file if present
load_dotenv()

# CLI configurations
CLI_CONTEXT_SETTINGS: dict[str, Any] = {
    "help_option_names": ["-h", "--help"],
}

# AI Agent default settings
DEFAULT_LLM_MODEL: str = os.getenv("LLM_MODEL", "openai:gpt-4o")
SYSTEM_PROMPT: str = (
    "You are a helpful, professional, and highly capable AI assistant. "
    "Use clean markdown formatting for code blocks, bullet points, and headers."
)
```

```python
# [NEW FILE] src/core/agent.py
"""Core Agent definition and conversation logic using PydanticAI v2."""

from typing import AsyncGenerator
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage
from src.config import DEFAULT_LLM_MODEL, SYSTEM_PROMPT

# Instantiate the PydanticAI Agent with sensible defaults.
# PydanticAI v2 will automatically fetch the correct api_key from the corresponding 
# environment variable (e.g., OPENAI_API_KEY).
chat_agent = Agent(
    model=DEFAULT_LLM_MODEL,
    system_prompt=SYSTEM_PROMPT,
)


class AgentService:
    """Service to interact with the PydanticAI Agent in a clean, decoupled manner."""

    def __init__(self, agent: Agent[None, str] = chat_agent) -> None:
        """Initialize the agent service."""
        self._agent = agent

    async def stream_response(
        self, 
        prompt: str, 
        history: list[ModelMessage]
    ) -> AsyncGenerator[tuple[str, list[ModelMessage]], None]:
        """Send a prompt to the agent and stream the text response incrementally.

        Yields:
            A tuple of (incremental_text_chunk, updated_model_messages).
        """
        # run_stream acts as an async context manager in PydanticAI
        async with self._agent.run_stream(prompt, message_history=history) as result:
            async for text_chunk in result.stream_text():
                yield text_chunk, result.all_messages()
```

---

### Phase 3: Textual TUI Application Implementation
We will build the TUI app that handles user interactions and reactive state. We will write an external TCSS file to keep styles organized.

```css
/* [NEW FILE] src/tui/styles.tcss */

/* Global container styling */
Screen {
    background: $background;
}

#app-title {
    background: $primary;
    color: $text;
    text-align: center;
    text-style: bold;
    height: 3;
    content-align: center middle;
}

#chat-container {
    height: 1fr;
    width: 100%;
    background: $surface;
    border: tall $primary-muted;
    padding: 1 2;
    overflow-y: scroll;
}

/* Chat message widgets spacing and base rules */
ChatMessage {
    margin: 1 0;
    padding: 1 2;
    background: $background-lighten-1;
    border-radius: 3;
    width: 100%;
    height: auto;
}

.user-message {
    border-left: solid $accent;
    background: $boost;
}

.agent-message {
    border-left: solid $success;
}

/* User Input layout */
#input-container {
    dock: bottom;
    height: auto;
    width: 100%;
    background: $background;
    padding: 1 0 0 0;
}

Input {
    border: double $primary;
    width: 100%;
    height: 3;
}
```

```python
# [NEW FILE] src/tui/app.py
"""Terminal User Interface application built with Textual."""

from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Vertical
from textual.widgets import Header, Footer, Static, Input
from rich.markdown import Markdown

from pydantic_ai.messages import ModelMessage
from src.core.agent import AgentService


class ChatMessage(Static):
    """Base class representing a chat bubble."""
    pass


class UserMessage(ChatMessage):
    """Widget to render user prompts cleanly."""

    def __init__(self, content: str) -> None:
        super().__init__()
        self.content = content

    def render(self) -> str:
        return f"[bold blue]You:[/bold blue]\n{self.content}"


class AgentMessage(ChatMessage):
    """Widget to render AI agent responses dynamically using Rich Markdown."""

    def __init__(self, content: str = "") -> None:
        super().__init__()
        self.content = content

    def update_text(self, text: str) -> None:
        self.content = text
        # Overwrite content using Markdown formatting
        self.update(Markdown(self.content))


class ChatApp(App[None]):
    """Textual TUI Chat Application."""

    # Point to our external TCSS stylesheet
    CSS_PATH = "styles.tcss"
    
    # Key bindings
    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+r", "clear_chat", "Reset Chat History"),
    ]

    def __init__(self, agent_service: AgentService | None = None) -> None:
        super().__init__()
        self.agent_service = agent_service or AgentService()
        self.conversation_history: list[ModelMessage] = []

    def compose(self) -> ComposeResult:
        """Define layouts and widget composition."""
        yield Static("PydanticAI v2 — Chat Assistant", id="app-title")
        yield Header(show_clock=True)
        
        # Houses the chat dialogue
        with VerticalScroll(id="chat-container"):
            pass
            
        with Vertical(id="input-container"):
            yield Input(placeholder="Type your message here and press Enter...", id="user-input")
            
        yield Footer()

    async def on_mount(self) -> None:
        """Actions to execute on app load."""
        self.query_one(Input).focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle incoming user prompts asynchronously."""
        user_prompt = event.value.strip()
        if not user_prompt:
            return

        # Clear input field immediately for responsiveness
        input_widget = self.query_one("#user-input", Input)
        input_widget.value = ""

        chat_container = self.query_one("#chat-container", VerticalScroll)

        # 1. Mount and scroll to User Message
        user_msg = UserMessage(user_prompt)
        user_msg.add_class("user-message")
        await chat_container.mount(user_msg)
        user_msg.scroll_visible()

        # 2. Mount and scroll to dynamic Agent Message placeholder
        agent_msg = AgentMessage()
        agent_msg.add_class("agent-message")
        await chat_container.mount(agent_msg)
        agent_msg.scroll_visible()

        # Disable input field while fetching streaming content to prevent race conditions
        input_widget.disabled = True

        accumulated_text = ""
        try:
            # Consume stream chunks asynchronously
            async for chunk, updated_history in self.agent_service.stream_response(
                user_prompt, self.conversation_history
            ):
                accumulated_text += chunk
                agent_msg.update_text(accumulated_text)
                
                # Dynamic scroll handling as messages expand
                chat_container.scroll_to_widget(agent_msg)
            
            # Commit the full conversation turn history
            self.conversation_history = updated_history
            
        except Exception as e:
            agent_msg.update(f"[bold red]System Error:[/bold red] {str(e)}")
        finally:
            input_widget.disabled = False
            input_widget.focus()

    async def action_clear_chat(self) -> None:
        """Action handler to clear the screen and wipe the conversation history."""
        self.conversation_history.clear()
        chat_container = self.query_one("#chat-container", VerticalScroll)
        
        # Remove all nested widgets inside the container
        for widget in list(chat_container.children):
            await widget.remove()
            
        self.notify("Conversation history reset successfully!")
```

---

### Phase 4: CLI Routing Interface
We will integrate a command-line interface entrypoint using `Typer` to boot our chat application effortlessly.

```python
# [NEW FILE] src/cli.py
"""Command Line Interface command router."""

import typer
from src.config import CLI_CONTEXT_SETTINGS
from src.tui.app import ChatApp

# Setup Typer application with strict conventions
app = typer.Typer(
    context_settings=CLI_CONTEXT_SETTINGS,
    no_args_is_help=False,  # Runs the TUI by default
)


@app.command()
def chat() -> None:
    """Launch the interactive Terminal User Interface (TUI) Chat Assistant."""
    tui_app = ChatApp()
    tui_app.run()


@app.callback(invoke_without_command=True)
def default_run(ctx: typer.Context) -> None:
    """Entry point route when cli.py is executed directly without subcommands."""
    if ctx.invoked_subcommand is None:
        chat()


if __name__ == "__main__":
    app()
```

Create base entry files inside `src` folder:
```python
# [NEW FILE] src/__init__.py
"""Initialization module for the PydanticAI Textual Chat application."""

__version__ = "0.1.0"
```

---

### Phase 5: Housekeeping & Documentation updates
Ensure build artifacts are properly ignored, document steps for usage, and maintain a project changelog.

```text
# [MODIFY] .gitignore
# Ensure we ignore Textual log outputs or standard python virtual env variables
.env
.tcss.log
.venv/
__pycache__/
*.pyc
```

```markdown
# [MODIFY] README.md
# Update user documentation to explain setup and launch steps.

## AI Chat Terminal (TUI)

An interactive terminal user interface (TUI) powered by **PydanticAI v2** and **Textual**.

### Installation and Setup
1. Clone the repository.
2. Initialize virtual environment and install packages via `uv`:
   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install -e ".[dev]"
   ```
3. Copy `.env.example` to `.env` and assign your API credentials:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

### Running the App
Run the standard CLI commands:
```bash
uv run python -m src.cli
```
* **Ctrl + Q**: Quit the app.
* **Ctrl + R**: Clear chat memory and screen.
```

```markdown
# [NEW FILE] CHANGELOG.md
# Keep a changelog of project changes.

# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-07-26
### Added
- Created an interactive Terminal User Interface (TUI) using Textual.
- Implemented asynchronous stream handling utilizing PydanticAI v2 API bindings.
- Created `cli.py` commands powered by Typer.
- Included customizable styles file `styles.tcss` for responsive layout designs.
```

---

### Phase 6: Implementation Report Creation
Upon successful execution, the agent should output a detailed report describing the final deployment details.

```markdown
# [NEW FILE] _ai/backlog/reports/260726_1939__IMPLEMENTATION_REPORT__pydanticai_v2_textual_chat.md
---
filename: "_ai/backlog/reports/260726_1939__IMPLEMENTATION_REPORT__pydanticai_v2_textual_chat.md"
title: "Report: Implement Textual Chat Interface powered by PydanticAI v2"
createdAt: 2026-07-26 19:39
updatedAt: 2026-07-26 19:39
planFile: "_ai/backlog/active/260726_1939__IMPLEMENTATION_PLAN__pydanticai_v2_textual_chat.md"
project: "Python Project"
status: completed
filesCreated: 6
filesModified: 3
filesDeleted: 0
tags: [python, textual, tui, pydantic-ai, llm, report]
documentType: IMPLEMENTATION_REPORT
---

## 1. Summary
We have successfully implemented a high-performance, asynchronous Terminal User Interface (TUI) powered by Textual and backed by PydanticAI v2. The system splits concerns securely, allowing stable token-by-token text streaming without interface lagging.

## 2. Files Changed
### Created
- `src/__init__.py`: Package entry declaration.
- `src/config.py`: Configuration and default settings.
- `src/core/agent.py`: Interface managing model settings and PydanticAI runtime stream handlers.
- `src/tui/app.py`: Textual visual elements, layouts, key bindings, and input streaming mechanisms.
- `src/tui/styles.tcss`: UI color design, boundaries, padding, and alignments.
- `CHANGELOG.md`: Log of updates.

### Modified
- `pyproject.toml`: Dependency configuration (added textual, pydantic-ai, etc.).
- `.gitignore`: Ignored cache files, environment directories, and `.tcss.log`.
- `README.md`: Added setup and operation notes.

## 3. Key Changes
- **Async Streaming Integration**: Utilizes PydanticAI v2's `run_stream()` async engine cleanly alongside Textual's async message handlers.
- **Isolate Architecture**: Decoupled LLM client processes from layout structures ensuring SOLID rules.
- **Keystroke Events**: Enabled immediate clearing of the stream history and clean terminal exit sequences using `Ctrl + R` and `Ctrl + Q`.

## 4. Deviations from Plan
*(Leave empty for the agent to fill in if anything changes during implementation).*

## 5. Technical Decisions
- **Textual Markdown Renderable**: Implemented inside `AgentMessage` widget to automatically translate raw LLM response chunks into Rich-formatted terminal segments instantly.
- **ModelMessage Memory Storage**: Tracked conversation turns as native PydanticAI message lists to ensure full compatibility with modern multi-turn operations.

## 6. Testing Notes
Verify deployment:
- Run formatting controls: `uv run black . && uv run ruff check .`
- Execute runtime to verify stream capabilities: `uv run python -m src.cli`
```
