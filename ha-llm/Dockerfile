ARG BUILD_FROM="ghcr.io/home-assistant/base:latest"
FROM $BUILD_FROM

# Install Python 3 and pip
RUN apk add --no-cache python3 py3-pip py3-wheel gcc musl-dev python3-dev libffi-dev

WORKDIR /app

# Install dependencies first (layer cache)
COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Copy application source
COPY app/ ./app/

# Copy s6-overlay service scripts (run/finish must be executable)
COPY rootfs/ /
RUN chmod a+x \
    /etc/s6-overlay/s6-rc.d/llm-wrapper/run \
    /etc/s6-overlay/s6-rc.d/llm-wrapper/finish

EXPOSE 8080
