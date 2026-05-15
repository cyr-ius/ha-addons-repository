# Ollama — Home Assistant Add-on

Runs a local [Ollama](https://ollama.ai) instance directly inside Home
Assistant OS. No external server needed.

## Features

- Installs the official Ollama binary at build time (no Docker-in-Docker)
- Automatically pulls configured models on first start
- Exposes the standard Ollama API on port `11434`
- Reachable by other add-ons as `http://ha_ollama:11434`
- Models stored in `/data/ollama/models` (persists across restarts)

## Configuration

| Option | Default | Description |
|---|---|---|
| `models` | `["llama3.2"]` | List of models to pull on startup |
| `keep_alive` | `5m` | How long to keep a model loaded in memory after last use |
| `max_loaded_models` | `1` | Max models loaded simultaneously (RAM constraint) |
| `gpu_layers` | `0` | Layers offloaded to GPU — `0` = CPU only |
| `num_threads` | `4` | CPU threads used for inference |
| `data_dir` | `/data/ollama` | Where models are stored |

### Example configuration

```yaml
models:
  - llama3.2
  - phi3:mini
keep_alive: 10m
max_loaded_models: 1
gpu_layers: 0
num_threads: 4
data_dir: /data/ollama
```

## Recommended models by hardware

| Hardware | Model | VRAM / RAM |
|---|---|---|
| VM 8 GB | `llama3.2` | ~5 GB |
| VM 16 GB | `llama3.1:8b` | ~8 GB |
| Raspberry Pi 5 8 GB | `phi3:mini` | ~3 GB |
| Server 32 GB | `mistral:7b` | ~6 GB |

## First start

Model pulls happen automatically on startup and can take several minutes
depending on model size and network speed. Check the add-on logs to follow
the download progress.

```
[ha-ollama] Checking model: llama3.2
[ha-ollama]   ↓ pulling llama3.2 (this may take several minutes)...
[ha-ollama]   ✓ llama3.2 pulled successfully
[ha-ollama] Ollama is ready. Loaded models: llama3.2
```

## Upgrading Ollama

The Ollama binary is baked into the Docker image at build time. To upgrade:

1. In the repository, dispatch the **Release** workflow with the desired bump
2. GitHub Actions will download the latest Ollama binary and rebuild

Or manually trigger a build with a specific Ollama version via the
`workflow_dispatch` input in `.github/workflows/build.yml`.
