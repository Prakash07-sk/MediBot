FROM python:3.10-slim

WORKDIR /app

# Upgrade pip
RUN pip install --upgrade pip

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy scripts & data
COPY ingest.py .
COPY data/ ./data/

# Expose Chroma port
EXPOSE 5000

# Set environment variables to disable OpenTelemetry
ENV OTEL_SDK_DISABLED=true
ENV CHROMA_OTEL_ENABLED=false
ENV OTEL_TRACES_EXPORTER=none
ENV OTEL_METRICS_EXPORTER=none

# Run Chroma and ingest data
CMD chroma run --host 0.0.0.0 --port 5000 --path /app/chroma & \
    python ingest.py && \
    tail -f /dev/null
