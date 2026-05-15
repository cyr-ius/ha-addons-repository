ARG BUILD_FROM
FROM $BUILD_FROM

# TARGETARCH is set automatically by Docker Buildx: amd64 or arm64
ARG TARGETARCH

# Ollama release to install — must match DEFAULT_OLLAMA_VERSION in build-ollama.yml
ARG OLLAMA_VERSION="0.24.0"

# curl: download, ca-certificates: HTTPS, bash+jq: s6 scripts
# zstd: extract .tar.zst archives (format used by Ollama since v0.24.0)
RUN apk add --no-cache curl ca-certificates bash jq zstd

# Download the official Ollama tarball (binary + lib/ollama/ GPU runtime libs).
# Extracting to /usr/local gives:
#   /usr/local/bin/ollama
#   /usr/local/lib/ollama/   ← CUDA / ROCm runners
#
# Format history (same logic as install.sh from ollama.com):
#   < v0.24.0  → .tgz   (fallback)
#   ≥ v0.24.0  → .tar.zst
RUN set -eux; \
    case "${TARGETARCH}" in \
        amd64)  OLLAMA_ARCH="amd64" ;; \
        arm64)  OLLAMA_ARCH="arm64" ;; \
        *)      echo "Unsupported arch: ${TARGETARCH}" && exit 1 ;; \
    esac; \
    BASE="https://github.com/ollama/ollama/releases/download/v${OLLAMA_VERSION}"; \
    if curl --fail --silent --head "${BASE}/ollama-linux-${OLLAMA_ARCH}.tar.zst" >/dev/null 2>&1; then \
        curl -fsSL "${BASE}/ollama-linux-${OLLAMA_ARCH}.tar.zst" \
            | zstd -d | tar -xf - -C /usr/local; \
    else \
        curl -fsSL "${BASE}/ollama-linux-${OLLAMA_ARCH}.tgz" \
            | tar -xzf - -C /usr/local; \
    fi; \
    ollama --version

COPY rootfs/ /

EXPOSE 11434
