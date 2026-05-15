"""
Home Assistant Core API client.

All requests are authenticated with the Supervisor token that HA injects
as the SUPERVISOR_TOKEN environment variable, or with the token set in
the add-on options (useful for development outside the Supervisor).
"""
import logging
import os
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _get_token() -> str:
    """
    Resolve the HA bearer token.

    Priority:
    1. SUPERVISOR_TOKEN env var — automatically set by HA when hassio_api: true
    2. ha_token option — manual override (useful for dev / external HA)
    """
    token = os.environ.get("SUPERVISOR_TOKEN") or get_settings().ha_token
    if not token:
        raise RuntimeError(
            "No HA token available. Set SUPERVISOR_TOKEN env var or ha_token option."
        )
    return token


def _build_headers() -> dict[str, str]:
    """Return HTTP headers for HA Core API requests."""
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Content-Type": "application/json",
    }


async def get_states() -> list[dict[str, Any]]:
    """
    Fetch all entity states from HA.

    Returns:
        List of state dicts, each containing entity_id, state, attributes.

    Raises:
        httpx.HTTPStatusError: On non-2xx response from HA.
    """
    settings = get_settings()
    url = f"{settings.ha_url}/api/states"

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, headers=_build_headers())
        response.raise_for_status()
        states: list[dict[str, Any]] = response.json()
        logger.debug("Fetched %d entity states from HA", len(states))
        return states


async def get_state(entity_id: str) -> dict[str, Any]:
    """
    Fetch the state of a single entity.

    Args:
        entity_id: HA entity identifier, e.g. "light.living_room".

    Returns:
        State dict with entity_id, state, attributes, last_changed, etc.

    Raises:
        httpx.HTTPStatusError: If entity not found (404) or other error.
    """
    settings = get_settings()
    url = f"{settings.ha_url}/api/states/{entity_id}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, headers=_build_headers())
        response.raise_for_status()
        return response.json()


async def call_service(
    domain: str,
    service: str,
    service_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Call a Home Assistant service.

    Args:
        domain:       Service domain, e.g. "light", "switch", "climate".
        service:      Service name, e.g. "turn_on", "turn_off", "set_temperature".
        service_data: Optional payload, e.g. {"entity_id": "light.kitchen", "brightness": 200}.

    Returns:
        HA response dict (list of affected states).

    Raises:
        httpx.HTTPStatusError: On non-2xx response from HA.
    """
    settings = get_settings()
    url = f"{settings.ha_url}/api/services/{domain}/{service}"
    payload = service_data or {}

    logger.info("Calling HA service %s.%s with data=%s", domain, service, payload)

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, headers=_build_headers(), json=payload)
        response.raise_for_status()
        return response.json()
