"""
Application configuration loaded from Home Assistant Supervisor options.
The Supervisor writes add-on options to /data/options.json at startup.
"""
from functools import lru_cache
import json
import logging
from pathlib import Path

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

_OPTIONS_PATH = Path("/data/options.json")


def _load_options() -> dict:
    """Load add-on options written by the HA Supervisor."""
    if _OPTIONS_PATH.exists():
        with _OPTIONS_PATH.open() as f:
            return json.load(f)
    # Fallback for local development
    logger.warning("options.json not found, using environment variables / defaults")
    return {}


class Settings(BaseSettings):
    """Add-on settings — values come from /data/options.json."""

    # Ollama endpoint (the Ollama add-on or an external instance)
    ollama_host: str = "http://homeassistant.local:11434"

    # LLM model name as registered in Ollama
    model: str = "llama3"

    # Maximum tokens the LLM may generate per turn
    max_tokens: int = 1024

    # Model context window in tokens
    context_window: int = 8192

    # Long-lived HA token — injected by Supervisor via SUPERVISOR_TOKEN env var
    # or overridden manually in options
    ha_token: str = ""

    # Home Assistant Core API base URL (accessible from inside the add-on)
    ha_url: str = "http://supervisor/core"

    # System prompt prepended to every conversation
    system_prompt: str = (
        "You are a smart home assistant controlling Home Assistant. "
        "You have access to tools to read sensor states and call services. "
        "Always respond in the same language as the user. "
        "Be concise and confirm every action you take."
    )

    model_config = {"env_prefix": "HA_LLM_"}


@lru_cache
def get_settings() -> Settings:
    """Return cached settings, merging options.json over defaults."""
    opts = _load_options()
    return Settings(**opts)
