ARG BUILD_FROM="ghcr.io/home-assistant/base-ubuntu:latest"

FROM ollama/ollama:latest AS ollama

FROM $BUILD_FROM

# TARGETARCH is set automatically by Docker Buildx: amd64 or arm64
ARG TARGETARCH

# curl: download, ca-certificates: HTTPS, bash+jq: s6 scripts
# zstd: extract .tar.zst archives (format used by Ollama since v0.24.0)
COPY --from=ollama /usr/bin/ollama /usr/bin/ollama
COPY --from=ollama /usr/lib/ollama/libggml-cpu-* /usr/lib/ollama/
COPY --from=ollama /usr/lib/ollama/libggml-base.so /usr/lib/ollama/libggml-base.so

ENV OLLAMA_HOST=0.0.0.0

COPY rootfs/ /

EXPOSE 11434
