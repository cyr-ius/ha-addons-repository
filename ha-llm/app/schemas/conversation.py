"""
Pydantic schemas for the conversation API.

We expose an OpenAI-compatible /v1/chat/completions endpoint so that
Home Assistant's custom conversation integration can talk to us without
any custom glue code.

Streaming (SSE) format follows the OpenAI spec:
  - Each chunk is a JSON object serialised as: data: {json}\\n\\n
  - The stream terminates with: data: [DONE]\\n\\n
  - Delta chunks carry a partial content string in choices[0].delta.content
  - Tool calls are NOT streamed — they are resolved silently before the final
    text stream begins (see ollama_client.py for the rationale).
"""
from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    """Single message in a conversation."""

    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request."""

    model: str = Field(default="", description="Model name — ignored, uses add-on config.")
    messages: list[ChatMessage] = Field(..., min_length=1)
    max_tokens: int | None = Field(default=None, ge=1, le=32768)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    stream: bool = False


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class ChatMessageResponse(BaseModel):
    """Assistant message in the response."""

    role: Literal["assistant"] = "assistant"
    content: str


class ChatChoice(BaseModel):
    """Single choice in a completion response."""

    index: int = 0
    message: ChatMessageResponse
    finish_reason: Literal["stop", "length", "tool_calls"] = "stop"


class UsageInfo(BaseModel):
    """Token usage — approximate, Ollama may not always return this."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response."""

    id: str = "chatcmpl-ha-llm"
    object: str = "chat.completion"
    model: str
    choices: list[ChatChoice]
    usage: UsageInfo = UsageInfo()


# ---------------------------------------------------------------------------
# Streaming (SSE) schemas
# ---------------------------------------------------------------------------


class DeltaContent(BaseModel):
    """Partial content fragment in a streaming chunk."""

    role: Literal["assistant"] | None = None
    content: str | None = None


class StreamChoice(BaseModel):
    """Single choice inside a streaming chunk."""

    index: int = 0
    delta: DeltaContent
    finish_reason: Literal["stop", "length", "tool_calls"] | None = None


class ChatCompletionChunk(BaseModel):
    """
    OpenAI-compatible SSE chunk.

    Serialised as: data: {json}\\n\\n
    Final sentinel: data: [DONE]\\n\\n
    """

    id: str = "chatcmpl-ha-llm"
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    model: str
    choices: list[StreamChoice]


# ---------------------------------------------------------------------------
# Health check schema
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """Response for /health endpoint."""

    status: Literal["ok", "degraded"] = "ok"
    ollama_reachable: bool = True
    model: str = ""
    ha_reachable: bool = True
