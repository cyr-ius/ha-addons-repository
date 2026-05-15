ARG BUILD_FROM
FROM $BUILD_FROM

# Install Python 3 and pip
RUN apk add --no-cache python3 py3-pip py3-wheel gcc musl-dev python3-dev libffi-dev

WORKDIR /app

# Install dependencies first (layer cache)
COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Copy application source
COPY app/ ./app/

# Copy s6-overlay service scripts
COPY rootfs/ /

# Expose the API port
EXPOSE 8080

CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
