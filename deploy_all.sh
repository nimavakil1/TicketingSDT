#!/bin/bash
# Full System Deployment Script
# Deploys both frontend and backend

set -e  # Exit on error

echo "=========================================="
echo "Full System Deployment"
echo "=========================================="
echo

# Check if running from project root
if [ ! -d "frontend" ] || [ ! -d "src" ]; then
    echo "Error: Must run from project root directory"
    exit 1
fi

# Pull latest changes
echo "[1/5] Pulling latest changes from git..."
git pull origin master

# Build frontend
echo
echo "[2/5] Building frontend..."
cd frontend
npm install --silent
npm run build
cd ..

# Check if build succeeded
if [ ! -d "frontend/dist" ]; then
    echo "Error: Build failed - dist directory not created"
    exit 1
fi

# Update backend dependencies
echo
echo "[3/5] Updating backend dependencies..."
source venv/bin/activate
pip install -q -r requirements.txt 2>/dev/null || true

# Restart backend
echo
echo "[4/5] Restarting backend..."
pkill -f "uvicorn.*web_api" 2>/dev/null || true
sleep 2
nohup uvicorn src.api.web_api:app --host 0.0.0.0 --port 8003 --workers 1 > nohup.out 2>&1 &
sleep 2

# Check if backend started
if pgrep -f "uvicorn.*web_api" > /dev/null; then
    echo "✓ Backend started successfully"
else
    echo "⚠ Warning: Backend may not have started"
fi

# Reload nginx
echo
echo "[5/5] Reloading nginx..."
sudo systemctl reload nginx

echo
echo "=========================================="
echo "✅ Full deployment completed!"
echo "=========================================="
echo
echo "Services:"
echo "  Frontend: https://ai.distri-smart.com"
echo "  Backend:  http://localhost:8003"
echo
echo "Check backend logs: tail -f ~/TicketingSDT/nohup.out"
