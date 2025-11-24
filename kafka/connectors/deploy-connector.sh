#!/bin/bash
# Script to deploy Kafka Connect sink connector for telescope data

set -e

CONNECT_URL="${CONNECT_URL:-http://localhost:8083}"
CONFIG_FILE="postgres-sink.json"

echo "Waiting for Kafka Connect to be ready..."
until curl -f -s "${CONNECT_URL}/" > /dev/null; do
    echo "Kafka Connect is unavailable - sleeping"
    sleep 5
done

echo "Kafka Connect is ready!"

# Check if connector already exists
CONNECTOR_NAME=$(jq -r '.name' "$CONFIG_FILE")
if curl -f -s "${CONNECT_URL}/connectors/${CONNECTOR_NAME}" > /dev/null 2>&1; then
    echo "Connector '${CONNECTOR_NAME}' already exists. Updating..."
    curl -X PUT \
        -H "Content-Type: application/json" \
        --data @"$CONFIG_FILE" \
        "${CONNECT_URL}/connectors/${CONNECTOR_NAME}/config"
else
    echo "Creating connector '${CONNECTOR_NAME}'..."
    curl -X POST \
        -H "Content-Type: application/json" \
        --data @"$CONFIG_FILE" \
        "${CONNECT_URL}/connectors"
fi

echo ""
echo "Connector deployment complete!"
echo "Check status with: curl ${CONNECT_URL}/connectors/${CONNECTOR_NAME}/status"
