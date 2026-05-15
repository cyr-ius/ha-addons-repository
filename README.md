# Local LLM for Home Assistant — Add-on Repository

This repository contains two Home Assistant add-ons that together bring a
fully local LLM conversation agent to your smart home.

## Add-ons

### 🦙 Ollama
Runs a local [Ollama](https://ollama.ai) instance inside Home Assistant.
Manages model storage and exposes an OpenAI-compatible API on port 11434.

**Install first.** Pull your preferred model (e.g. `llama3.2`) from the add-on options.

### 🤖 LLM Wrapper
Connects Home Assistant's Assist pipeline to the Ollama add-on.
Injects live entity states into the system prompt and handles tool calling
(turn on lights, set thermostat, etc.).

**Install second**, after Ollama is running.

---

## Installation

1. In Home Assistant: **Settings → Add-ons → Add-on Store → ⋮ → Repositories**
2. Paste: `https://github.com/cyr-ius/ha-addons-repository`
3. Install **Ollama** first, configure your model, start it and wait for the model to pull
4. Install **LLM Wrapper**, start it
5. In **Settings → Voice Assistants**, select *LLM Wrapper* as the conversation agent

## Recommended models by hardware

| Hardware | Recommended model | RAM required |
|---|---|---|
| VM / NUC (8 GB RAM) | `llama3.2` | ~5 GB |
| VM / NUC (16 GB RAM) | `llama3.1:8b` | ~8 GB |
| Raspberry Pi 5 (8 GB) | `phi3:mini` | ~3 GB |
| Server (32 GB RAM) | `mistral:7b` | ~6 GB |

## Network topology

```
Home Assistant
├── Assist pipeline  (STT / TTS)
│       ↓  POST /v1/chat/completions
├── LLM Wrapper add-on  (:8080)
│       ↓  http://ha_ollama:11434
└── Ollama add-on  (:11434)
            └── models/llama3.2, mistral, …
```

The two add-ons communicate over the Supervisor's internal network using
the add-on slug as hostname (`ha_ollama`). No external network required.
