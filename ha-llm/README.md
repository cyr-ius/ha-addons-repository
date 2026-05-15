# HA LLM Wrapper — Home Assistant Add-on

Local LLM conversation agent for Home Assistant, powered by Ollama.

Exposes an **OpenAI-compatible API** that the HA Assist pipeline can use as a
custom conversation backend, with live entity state injection and full
tool-calling support (turn on lights, set thermostat, etc.).

---

## Architecture

```
User (voice)
    │
    ▼
HA Assist pipeline  (STT → conversation agent → TTS)
    │
    ▼  POST /v1/chat/completions
HA LLM Wrapper add-on  ◄── this repo
    │   • builds system prompt with live HA states
    │   • executes tool calls against HA API
    ▼
Ollama add-on  (Llama 3 / Mistral / Phi-3 …)
```

---

## Prerequisites

| Requirement | Version |
|---|---|
| Home Assistant OS or Supervised | 2024.1+ |
| [Ollama add-on](https://github.com/home-assistant-community-add-ons/ollama) | latest |
| A pulled model in Ollama | e.g. `llama3`, `mistral`, `phi3` |

Pull a model from the Ollama add-on terminal:

```bash
ollama pull llama3
# or
ollama pull mistral
```

---

## Installation

1. In HA → **Settings → Add-ons → Add-on Store → ⋮ → Repositories**
2. Add: `https://github.com/YOUR_USERNAME/ha-llm-addon`
3. Install **LLM Wrapper for Home Assistant**
4. Configure options (see below)
5. Start the add-on

---

## Configuration

| Option | Default | Description |
|---|---|---|
| `ollama_host` | `http://homeassistant.local:11434` | URL of your Ollama instance |
| `model` | `llama3` | Model name as listed in `ollama list` |
| `max_tokens` | `1024` | Max tokens generated per turn |
| `context_window` | `8192` | Model context window size |
| `ha_token` | _(empty)_ | Long-lived HA token — leave empty, Supervisor injects it automatically |
| `ha_url` | `http://supervisor/core` | HA Core API URL — do not change unless external HA |
| `system_prompt` | _(see config.yaml)_ | Customize the LLM persona and instructions |

---

## Connecting to the Assist pipeline

### Option A — Built-in OpenAI Conversation integration (simplest)

1. **Settings → Devices & Services → Add Integration → OpenAI Conversation**
2. Set **API key**: any string (e.g. `homeassistant`)
3. Set **API base URL**: `http://localhost:8080`
4. Set **Model**: match your `model` option (e.g. `llama3`)
5. In **Voice Assistants**, select this agent as the conversation backend

### Option B — `extended_openai_conversation` (HACS, more features)

Install via HACS, configure with the same base URL and model.

---

## Available tools

The LLM can call these tools automatically:

| Tool | Description |
|---|---|
| `get_entity_state` | Read the current state of any HA entity |
| `call_ha_service` | Call any HA service (light, switch, climate, etc.) |

Example interactions:
- *"Turn off all lights in the living room"*
- *"Set the bedroom thermostat to 19 degrees"*
- *"Is the front door locked?"*
- *"Play jazz on the kitchen speaker"*

---

## Development

```bash
# Local run (set env vars manually)
export HA_LLM_OLLAMA_HOST=http://localhost:11434
export HA_LLM_HA_URL=http://your-ha-ip:8123
export HA_LLM_HA_TOKEN=your_long_lived_token

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

API docs available at `http://localhost:8080/docs`

---

## Project structure

```
ha-llm-addon/
├── config.yaml                    # Add-on manifest
├── Dockerfile                     # Container image
├── requirements.txt
└── app/
    ├── main.py                    # FastAPI entry point
    ├── core/
    │   └── config.py              # Settings from /data/options.json
    ├── schemas/
    │   └── conversation.py        # Pydantic request/response models
    ├── services/
    │   ├── ha_client.py           # HA Core API client
    │   ├── ollama_client.py       # Ollama client + tool-call loop
    │   └── prompt_builder.py      # Dynamic system prompt with HA states
    └── api/v1/
        ├── router.py
        └── endpoints/
            ├── conversation.py    # POST /v1/chat/completions
            └── health.py          # GET /health
```
