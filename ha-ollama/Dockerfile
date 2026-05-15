ARG BUILD_FROM="ghcr.io/home-assistant/base-ubuntu:latest"
ARG VERSION="0.24.0"

FROM ollama/ollama:${VERSION} AS ollama
FROM ${BUILD_FROM}

COPY --from=ollama /usr/bin/ollama /usr/bin/ollama
COPY --from=ollama /usr/lib/ollama/libggml-cpu-* /usr/lib/ollama/
COPY --from=ollama /usr/lib/ollama/libggml-base.so /usr/lib/ollama/libggml-base.so

COPY rootfs/ /

EXPOSE 11434
