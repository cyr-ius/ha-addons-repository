"""
Conversation endpoint — OpenAI-compatible /v1/chat/completions.

Home Assistant's 'openai_conversation' custom component (and the built-in
one when pointed at a custom base URL) will POST here directly.

Streaming support:
  When request.stream is True, the endpoint returns a text/event-stream
  response.  Tool-calling rounds are resolved silently first (non-streamed),
  then the final LLM reply is forwarded token by token as SSE chunks.
  This lets the HA frontend / Lovelace display words as they arrive instead
  of waiting for the full answer.
"""
from collections.abc import AsyncGenerator
import logging

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.schemas.conversation import (
    ChatChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessageResponse,
)
from app.services.ollama_client import chat_completion, chat_completion_stream
from app.services.prompt_builder import build_system_prompt

logger = logging.getLogger(__name__)
router = APIRouter()


async def _prepare_messages(request: ChatCompletionRequest) -> tuple[list[dict], str]:
    """
    Build the system prompt and strip client-side system messages.

    Args:
        request: Incoming ChatCompletionRequest.

    Returns:
        Tuple of (user_messages, system_prompt).

    Raises:
        HTTPException 422: If no non-system messages are present.
    """
    settings = get_settings()

    try:
        system_prompt = await build_system_prompt()
    except Exception as exc:
        logger.error("Failed to build system prompt: %s", exc)
        system_prompt = settings.system_prompt

    user_messages = [
        m.model_dump(exclude_none=True)
        for m in request.messages
        if m.role != "system"
    ]

    if not user_messages:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one non-system message is required.",
        )

    return user_messages, system_prompt


@router.post(
    "/v1/chat/completions",
    summary="OpenAI-compatible chat completion proxied through Ollama",
    # We return either ChatCompletionResponse (JSON) or StreamingResponse (SSE)
    # FastAPI cannot declare both in response_model, so we leave it untyped here.
)
async def create_chat_completion(
    request: ChatCompletionRequest,
) -> ChatCompletionResponse | StreamingResponse:
    """
    Accept an OpenAI-style chat request, inject live HA context into the
    system prompt, forward to Ollama with tool definitions, execute any
    tool calls against HA, and return the final assistant reply.

    When ``stream=true``, the response is a Server-Sent Events stream
    (Content-Type: text/event-stream).  Each chunk follows the OpenAI delta
    format.  Tool-call rounds are always resolved non-streamed before the
    token stream begins.

    Args:
        request: ChatCompletionRequest with messages, stream flag, and params.

    Returns:
        ChatCompletionResponse (JSON) or StreamingResponse (SSE).

    Raises:
        HTTPException 502: If Ollama or HA is unreachable.
        HTTPException 422: If no user messages are provided.
    """
    settings = get_settings()
    user_messages, system_prompt = await _prepare_messages(request)

    # ------------------------------------------------------------------ #
    # Streaming path                                                       #
    # ------------------------------------------------------------------ #
    if request.stream:
        async def _event_generator() -> AsyncGenerator[str, None]:
            """Wrap chat_completion_stream and surface errors as SSE."""
            try:
                async for chunk in chat_completion_stream(
                    messages=user_messages,
                    system_prompt=system_prompt,
                ):
                    yield chunk
            except Exception as exc:
                logger.error("Streaming LLM completion failed: %s", exc)
                # Emit an error chunk so the client knows something went wrong
                yield f"data: {{\"error\": \"{exc}\"}}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(
            _event_generator(),
            media_type="text/event-stream",
            headers={
                # Prevent proxies / nginx from buffering the SSE stream
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    # ------------------------------------------------------------------ #
    # Non-streaming path (unchanged behaviour)                            #
    # ------------------------------------------------------------------ #
    try:
        answer = await chat_completion(
            messages=user_messages,
            system_prompt=system_prompt,
        )
    except Exception as exc:
        logger.error("LLM completion failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM backend error: {exc}",
        ) from exc

    return ChatCompletionResponse(
        model=settings.model,
        choices=[
            ChatChoice(
                message=ChatMessageResponse(content=answer),
                finish_reason="stop",
            )
        ],
    )
