#!/bin/bash
# Start the AI Agent Web UI
# This starts the FastAPI backend server

cd "$(dirname "$0")/.."

echo "Starting AI Support Agent Web UI..."
echo "API will be available at: http://localhost:8001"
echo "API Documentation at: http://localhost:8001/docs"
echo ""

python3 -m uvicorn src.api.web_api:app --host 0.0.0.0 --port 8001 --reload
