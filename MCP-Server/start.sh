#!/bin/bash
set -e

echo "Activating all workflows in the database..."

# Get list of all workflows (both active and inactive)
# Parse the output which is in format: ID|Name
WORKFLOWS=$(n8n list:workflow --output=json 2>&1 | grep -E '^[A-Za-z0-9]+\|' || true)

if [ -z "$WORKFLOWS" ]; then
  echo "No workflows found in database."
else
  echo "Found workflows. Activating them..."
  # Process each workflow line
  echo "$WORKFLOWS" | while IFS='|' read -r workflow_id workflow_name; do
    if [ -n "$workflow_id" ]; then
      echo "Activating workflow: $workflow_name (ID: $workflow_id)"
      n8n update:workflow --id="$workflow_id" --active=true 2>&1 | grep -v "deprecation" || true
    fi
  done
  echo "All workflows activated successfully."
fi

echo ""
echo "Starting n8n server..."
n8n start
