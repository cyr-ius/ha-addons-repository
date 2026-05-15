"""
Health check endpoint.

The HA Supervisor uses this to know whether the add-on is ready.
Also useful for debugging connectivity issues with Ollama and HA.
"""
import logging

from fastapi import APIRouter
import httpx

from app.core.config import get_settings
from app.schemas.conversation import HealthResponse
from app.services.ha_client import get_states

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Add-on health check",
)
async def health_check() -> HealthResponse:
    """
    Verify connectivity to Ollama and Home Assistant.

    Returns:
        HealthResponse with reachability flags and configured model name.
    """
    settings = get_settings()
    ollama_ok = False
    ha_ok = False

    # Check Ollama
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.ollama_host}/api/tags")
            ollama_ok = resp.status_code == 200
    except Exception as exc:
        logger.warning("Ollama unreachable: %s", exc)

    # Check HA Core API
    try:
        await get_states()
        ha_ok = True
    except Exception as exc:
        logger.warning("HA API unreachable: %s", exc)

    overall = "ok" if (ollama_ok and ha_ok) else "degraded"

    return HealthResponse(
        status=overall,
        ollama_reachable=ollama_ok,
        model=settings.model,
        ha_reachable=ha_ok,
    )
