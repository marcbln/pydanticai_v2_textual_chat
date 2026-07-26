import typer

from src.config import CLI_CONTEXT_SETTINGS
from src.tui.app import ChatApp

app = typer.Typer(
    context_settings=CLI_CONTEXT_SETTINGS,
    no_args_is_help=False,
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
