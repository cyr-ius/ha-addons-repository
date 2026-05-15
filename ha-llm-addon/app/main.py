"""
HA LLM Wrapper — FastAPI application entry point.

Exposes an OpenAI-compatible API that proxies requests to a local Ollama
instance, enriching each request with a live Home Assistant state snapshot
and tool-calling capabilities to control HA devices.
"""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Log startup/shutdown events and validate settings."""
    settings = get_settings()
    logger.info(
        "HA LLM Wrapper starting — model=%s, ollama=%s, ha=%s",
        settings.model,
        settings.ollama_host,
        settings.ha_url,
    )
    yield
    logger.info("HA LLM Wrapper shutting down.")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="HA LLM Wrapper",
    description=(
        "OpenAI-compatible LLM API for Home Assistant Assist pipeline. "
        "Routes requests to a local Ollama instance with live HA context injection "
        "and tool-calling support."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Allow requests from the HA frontend (same host, different port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routes
app.include_router(api_router)
