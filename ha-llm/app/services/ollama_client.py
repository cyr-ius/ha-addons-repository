"""
Ollama API client with tool-calling support.

Ollama exposes an OpenAI-compatible /v1/chat/completions endpoint when
running version ≥ 0.3. We use that endpoint directly so the same code
works with any OpenAI-compatible backend (Ollama, LM Studio, etc.).

Tool calling flow:
  1. Send messages + tools definition to Ollama.
  2. If the model replies with tool_calls, execute each tool against HA.
  3. Append tool results as tool-role messages and call the LLM again.
  4. Return the final text response.
"""
from collections.abc import AsyncGenerator
import json
import logging
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.ha_client import call_service, get_state

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool definitions exposed to the LLM
# ---------------------------------------------------------------------------

HA_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_entity_state",
            "description": (
                "Get the current state and attributes of a Home Assistant entity. "
                "Use this when you need fresh data about a specific device."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "The HA entity ID, e.g. 'sensor.living_room_temperature'.",
                    }
                },
                "required": ["entity_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "call_ha_service",
            "description": (
                "Call a Home Assistant service to control a device or trigger an automation. "
                "Examples: turn lights on/off, set thermostat temperature, lock a door."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Service domain, e.g. 'light', 'switch', 'climate'.",
                    },
                    "service": {
                        "type": "string",
                        "description": "Service name, e.g. 'turn_on', 'set_temperature'.",
                    },
                    "service_data": {
                        "type": "object",
                        "description": (
                            "Optional service payload. "
                            "Example: {\"entity_id\": \"light.kitchen\", \"brightness\": 200}"
                        ),
                    },
                },
                "required": ["domain", "service"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Tool executor
# ---------------------------------------------------------------------------


async def _execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """
    Dispatch a tool call to the appropriate HA client function.

    Args:
        name:      Tool name as declared in HA_TOOLS.
        arguments: Parsed JSON arguments from the LLM.

    Returns:
        JSON-encoded string result to feed back to the LLM.
    """
    try:
        if name == "get_entity_state":
            result = await get_state(arguments["entity_id"])
            return json.dumps(result)

        if name == "call_ha_service":
            result = await call_service(
                domain=arguments["domain"],
                service=arguments["service"],
                service_data=arguments.get("service_data"),
            )
            return json.dumps({"status": "ok", "result": result})

        return json.dumps({"error": f"Unknown tool: {name}"})

    except Exception as exc:
        logger.error("Tool '%s' execution failed: %s", name, exc)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Main completion function
# ---------------------------------------------------------------------------


async def chat_completion(
    messages: list[dict[str, Any]],
    system_prompt: str,
) -> str:
    """
    Send a conversation to Ollama and handle tool calls transparently.

    Args:
        messages:      Conversation history as OpenAI-style message dicts.
        system_prompt: Pre-built system prompt (includes HA state snapshot).

    Returns:
        Final assistant reply as plain text.

    Raises:
        httpx.HTTPStatusError: On non-2xx response from Ollama.
        RuntimeError: If the LLM loops tool calls more than allowed.
    """
    settings = get_settings()
    url = f"{settings.ollama_host}/v1/chat/completions"

    # Prepend system message
    full_messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        *messages,
    ]

    max_tool_rounds = 5  # Safety cap to prevent infinite tool loops

    async with httpx.AsyncClient(timeout=120.0) as client:
        for round_idx in range(max_tool_rounds + 1):
            payload = {
                "model": settings.model,
                "messages": full_messages,
                "tools": HA_TOOLS,
                "max_tokens": settings.max_tokens,
                "stream": False,
            }

            logger.debug(
                "Ollama request round %d — %d messages", round_idx, len(full_messages)
            )

            response = await client.post(url, json=payload)
            response.raise_for_status()
            data: dict[str, Any] = response.json()

            choice: dict[str, Any] = data["choices"][0]
            assistant_message: dict[str, Any] = choice["message"]
            finish_reason: str = choice.get("finish_reason", "stop")

            # No tool calls → we have the final answer
            if finish_reason != "tool_calls" or not assistant_message.get("tool_calls"):
                content: str = assistant_message.get("content") or ""
                logger.debug("Final answer received after %d round(s)", round_idx + 1)
                return content.strip()

            # Process each tool call sequentially
            full_messages.append(assistant_message)

            for tool_call in assistant_message["tool_calls"]:
                tool_name: str = tool_call["function"]["name"]
                raw_args: str = tool_call["function"].get("arguments", "{}")

                try:
                    tool_args: dict[str, Any] = json.loads(raw_args)
                except json.JSONDecodeError:
                    tool_args = {}

                logger.info("Executing tool: %s(%s)", tool_name, tool_args)
                tool_result: str = await _execute_tool(tool_name, tool_args)

                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": tool_result,
                })

        raise RuntimeError("LLM exceeded maximum tool-call rounds without a final answer.")


# ---------------------------------------------------------------------------
# Streaming completion (tool rounds non-streamed, final reply streamed)
# ---------------------------------------------------------------------------


async def chat_completion_stream(
    messages: list[dict[str, Any]],
    system_prompt: str,
) -> AsyncGenerator[str, None]:
    """
    Same as chat_completion but yields SSE-formatted text chunks for the
    final assistant reply.

    Strategy:
      - Tool-calling rounds are executed without streaming (we need the full
        response to parse tool_call JSON before dispatching to HA).
      - Once all tools are resolved and Ollama is ready to produce the final
        textual answer, we re-issue that last request with stream=True and
        forward each token chunk as an SSE line.

    Args:
        messages:      Conversation history as OpenAI-style message dicts.
        system_prompt: Pre-built system prompt (includes HA state snapshot).

    Yields:
        SSE-formatted strings: "data: {json}\\n\\n" per token chunk,
        terminated by "data: [DONE]\\n\\n".

    Raises:
        httpx.HTTPStatusError: On non-2xx response from Ollama.
        RuntimeError: If the LLM exceeds maximum tool-call rounds.
    """
    settings = get_settings()
    url = f"{settings.ollama_host}/v1/chat/completions"

    full_messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        *messages,
    ]

    max_tool_rounds = 5

    # --- Phase 1: resolve all tool calls (non-streamed) ---
    async with httpx.AsyncClient(timeout=120.0) as client:
        for round_idx in range(max_tool_rounds + 1):
            payload = {
                "model": settings.model,
                "messages": full_messages,
                "tools": HA_TOOLS,
                "max_tokens": settings.max_tokens,
                "stream": False,
            }

            logger.debug("Stream pre-flight round %d — %d messages", round_idx, len(full_messages))

            response = await client.post(url, json=payload)
            response.raise_for_status()
            data: dict[str, Any] = response.json()

            choice: dict[str, Any] = data["choices"][0]
            assistant_message: dict[str, Any] = choice["message"]
            finish_reason: str = choice.get("finish_reason", "stop")

            # No more tool calls → full_messages is ready for the streaming pass
            if finish_reason != "tool_calls" or not assistant_message.get("tool_calls"):
                logger.debug("Tool resolution done after %d round(s), streaming", round_idx + 1)
                break

            # Execute tools and append results
            full_messages.append(assistant_message)

            for tool_call in assistant_message["tool_calls"]:
                tool_name: str = tool_call["function"]["name"]
                raw_args: str = tool_call["function"].get("arguments", "{}")

                try:
                    tool_args: dict[str, Any] = json.loads(raw_args)
                except json.JSONDecodeError:
                    tool_args = {}

                logger.info("Executing tool (stream mode): %s(%s)", tool_name, tool_args)
                tool_result: str = await _execute_tool(tool_name, tool_args)

                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": tool_result,
                })
        else:
            raise RuntimeError("LLM exceeded maximum tool-call rounds without a final answer.")

    # --- Phase 2: stream the final answer ---
    stream_payload = {
        "model": settings.model,
        "messages": full_messages,
        # No tools on the final pass — we only want text output
        "max_tokens": settings.max_tokens,
        "stream": True,
    }

    async with (
        httpx.AsyncClient(timeout=120.0) as client,
        client.stream("POST", url, json=stream_payload) as response,
    ):
        response.raise_for_status()

        async for raw_line in response.aiter_lines():
            raw_line = raw_line.strip()

            if not raw_line or not raw_line.startswith("data:"):
                continue

            data_str = raw_line[len("data:"):].strip()

            if data_str == "[DONE]":
                yield "data: [DONE]\n\n"
                return

            try:
                chunk: dict[str, Any] = json.loads(data_str)
            except json.JSONDecodeError:
                logger.warning("Could not parse SSE chunk: %s", data_str)
                continue

            # Extract the delta content from the Ollama chunk
            choices = chunk.get("choices", [])
            if not choices:
                continue

            delta = choices[0].get("delta", {})
            finish = choices[0].get("finish_reason")
            content_piece: str | None = delta.get("content")

            # Build our own normalised chunk in OpenAI format
            out_chunk: dict[str, Any] = {
                "id": "chatcmpl-ha-llm",
                "object": "chat.completion.chunk",
                "model": settings.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": content_piece} if content_piece else {},
                        "finish_reason": finish,
                    }
                ],
            }

            yield f"data: {json.dumps(out_chunk)}\n\n"

    # Fallback sentinel if Ollama did not emit [DONE]
    yield "data: [DONE]\n\n"
