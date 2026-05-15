ARG BUILD_FROM
FROM $BUILD_FROM

# ── Build arguments injected by the HA builder / GitHub Actions ──────────────
# TARGETARCH is set by Docker Buildx during multi-platform builds:
#   amd64   → x86_64
#   arm64   → arm64 (aarch64)
ARG TARGETARCH

# Ollama release to install — bump this to upgrade
ARG OLLAMA_VERSION="0.3.14"

# ── System dependencies ───────────────────────────────────────────────────────
# curl        : download the Ollama binary
# ca-certificates : HTTPS verification
# bash        : s6 run scripts
# jq          : parse options.json in the run script
RUN apk add --no-cache curl ca-certificates bash jq

# ── Download the correct Ollama binary for this architecture ─────────────────
# Official release URLs:
#   https://github.com/ollama/ollama/releases/download/v<ver>/ollama-linux-amd64
#   https://github.com/ollama/ollama/releases/download/v<ver>/ollama-linux-arm64
RUN set -eux; \
    case "${TARGETARCH}" in \
        amd64)  OLLAMA_ARCH="amd64"  ;; \
        arm64)  OLLAMA_ARCH="arm64"  ;; \
        *)      echo "Unsupported arch: ${TARGETARCH}" && exit 1 ;; \
    esac; \
    curl -fsSL \
        "https://github.com/ollama/ollama/releases/download/v${OLLAMA_VERSION}/ollama-linux-${OLLAMA_ARCH}" \
        -o /usr/local/bin/ollama; \
    chmod +x /usr/local/bin/ollama; \
    ollama --version

# ── Copy s6-overlay service scripts ──────────────────────────────────────────
COPY rootfs/ /

# Ollama API port
EXPOSE 11434
