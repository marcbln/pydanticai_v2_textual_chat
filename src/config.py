import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

CLI_CONTEXT_SETTINGS: dict[str, Any] = {
    "help_option_names": ["-h", "--help"],
}

DEFAULT_LLM_MODEL: str = os.getenv("LLM_MODEL", "openai:gpt-4o")
SYSTEM_PROMPT: str = (
    "You are a helpful, professional, and highly capable AI assistant. "
    "Use clean markdown formatting for code blocks, bullet points, and headers."
)
