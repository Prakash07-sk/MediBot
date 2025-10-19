#!/bin/sh

# Set environment variables to disable OpenTelemetry
export OTEL_SDK_DISABLED=true
export CHROMA_OTEL_ENABLED=false
export OTEL_TRACES_EXPORTER=none
export OTEL_METRICS_EXPORTER=none

# Start ChromaDB server in background on port 5000
chroma run --host 0.0.0.0 --port 5000 --path /app/chroma &

# Wait a few seconds for Chroma to start
echo "⏳ Waiting for Chroma server..."
sleep 5

# Run ingestion script
python ingest.py

# Keep container alive
tail -f /dev/null
