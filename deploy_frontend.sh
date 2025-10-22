#!/bin/bash
# Frontend Deployment Script
# Automatically builds and deploys the frontend

set -e  # Exit on error

echo "=========================================="
echo "Frontend Deployment Script"
echo "=========================================="
echo

# Check if running from project root
if [ ! -d "frontend" ]; then
    echo "Error: Must run from project root directory"
    exit 1
fi

# Pull latest changes
echo "[1/4] Pulling latest changes from git..."
git pull origin master

# Build frontend
echo
echo "[2/4] Building frontend..."
cd frontend
npm install --silent
npm run build

# Check if build succeeded
if [ ! -d "dist" ]; then
    echo "Error: Build failed - dist directory not created"
    exit 1
fi

echo
echo "[3/4] Deployment location: /home/ai/TicketingSDT/frontend/dist"

# Reload nginx
echo
echo "[4/4] Reloading nginx..."
sudo systemctl reload nginx

echo
echo "=========================================="
echo "✅ Frontend deployed successfully!"
echo "=========================================="
echo
echo "The updated frontend is now live at:"
echo "  https://ai.distri-smart.com"
