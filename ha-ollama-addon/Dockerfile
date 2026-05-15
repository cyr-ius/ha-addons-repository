ARG BUILD_FROM
FROM $BUILD_FROM

# TARGETARCH is set automatically by Docker Buildx: amd64 or arm64
ARG TARGETARCH

# Ollama release to install — must match DEFAULT_OLLAMA_VERSION in build-ollama.yml
ARG OLLAMA_VERSION="0.3.14"

# curl: download, ca-certificates: HTTPS, bash+jq: s6 scripts
RUN apk add --no-cache curl ca-certificates bash jq

# Download the official Ollama tarball which includes the binary AND shared
# libraries (lib/ollama/) required for GPU acceleration (CUDA, ROCm).
# Extracting to /usr/local gives:
#   /usr/local/bin/ollama
#   /usr/local/lib/ollama/   ← GPU runtime libs
#
# Source: same logic as the official install.sh from ollama.com
RUN set -eux; \
    case "${TARGETARCH}" in \
        amd64)  OLLAMA_ARCH="amd64" ;; \
        arm64)  OLLAMA_ARCH="arm64" ;; \
        *)      echo "Unsupported arch: ${TARGETARCH}" && exit 1 ;; \
    esac; \
    curl -fsSL \
        "https://github.com/ollama/ollama/releases/download/v${OLLAMA_VERSION}/ollama-linux-${OLLAMA_ARCH}.tgz" \
        | tar -xzf - -C /usr/local; \
    ollama --version

COPY rootfs/ /

EXPOSE 11434
