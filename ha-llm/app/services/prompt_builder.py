"""
Dynamic system prompt builder.

Injects a snapshot of relevant HA entity states into the system prompt so
the LLM knows the current state of the home before answering.
"""
import logging
from typing import Any

from app.core.config import get_settings
from app.services.ha_client import get_states

logger = logging.getLogger(__name__)

# Domains we expose to the LLM — excludes noisy/irrelevant domains
_RELEVANT_DOMAINS = {
    "light",
    "switch",
    "cover",
    "climate",
    "sensor",
    "binary_sensor",
    "media_player",
    "alarm_control_panel",
    "lock",
    "fan",
    "vacuum",
    "scene",
    "script",
    "automation",
    "person",
    "device_tracker",
    "weather",
    "input_boolean",
    "input_number",
    "input_select",
    "input_text",
}

# Maximum number of entities injected to avoid blowing up the context window
_MAX_ENTITIES = 150


def _format_state(state: dict[str, Any]) -> str:
    """
    Format a single entity state as a compact text line.

    Args:
        state: HA state dict (entity_id, state, attributes).

    Returns:
        Human-readable one-liner, e.g.:
        "- light.living_room: on (brightness=200, color_temp=4000)"
    """
    entity_id: str = state["entity_id"]
    value: str = state["state"]
    attrs: dict[str, Any] = state.get("attributes", {})

    # Pick a small set of useful attributes to include
    interesting_attrs: dict[str, Any] = {}
    for key in (
        "friendly_name",
        "brightness",
        "color_temp",
        "temperature",
        "current_temperature",
        "hvac_mode",
        "fan_mode",
        "media_title",
        "volume_level",
        "battery",
        "unit_of_measurement",
        "device_class",
    ):
        if key in attrs and attrs[key] is not None:
            interesting_attrs[key] = attrs[key]

    if interesting_attrs:
        attrs_str = ", ".join(f"{k}={v}" for k, v in interesting_attrs.items())
        return f"- {entity_id}: {value} ({attrs_str})"

    return f"- {entity_id}: {value}"


async def build_system_prompt() -> str:
    """
    Build the full system prompt with a live snapshot of HA entities.

    Returns:
        String to be used as the "system" role message in the LLM request.
    """
    settings = get_settings()
    base_prompt: str = settings.system_prompt.strip()

    try:
        all_states: list[dict[str, Any]] = await get_states()
    except Exception as exc:
        logger.warning("Could not fetch HA states: %s", exc)
        all_states = []

    # Filter and cap the entity list
    relevant: list[dict[str, Any]] = [
        s
        for s in all_states
        if s["entity_id"].split(".")[0] in _RELEVANT_DOMAINS
    ][:_MAX_ENTITIES]

    if not relevant:
        return base_prompt

    entities_block = "\n".join(_format_state(s) for s in relevant)

    return (
        f"{base_prompt}\n\n"
        "## Current home state\n"
        "Below is a snapshot of your home devices. Use this to answer questions "
        "about current states and to decide which service to call.\n\n"
        f"{entities_block}"
    )
