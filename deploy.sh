#!/bin/bash
# Deployment script for TicketingSDT on server
# Run this after git pull

set -e  # Exit on error

echo "🚀 Starting deployment..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "$HOME/TicketingSDT/venv" ]; then
    source "$HOME/TicketingSDT/venv/bin/activate"
fi

# 1. Build frontend
echo "📦 Building frontend..."
cd ~/TicketingSDT/frontend
npm run build

# 2. Run any pending database migrations
echo "🗄️  Running database migrations..."
cd ~/TicketingSDT
python3 scripts/add_system_settings.py 2>/dev/null || echo "Migration already applied or failed"

# 3. Ensure admin user exists
echo "👤 Checking users..."
python3 scripts/ensure_admin_user.py

# 4. Restart backend service
echo "🔄 Restarting backend..."
pkill -f "uvicorn.*web_api" || echo "Backend not running"
nohup uvicorn src.api.web_api:app --host 0.0.0.0 --port 8003 > nohup.out 2>&1 &

echo "✅ Deployment complete!"
echo "Frontend: https://ai.distri-smart.com"
echo "Backend logs: tail -f ~/TicketingSDT/nohup.out"
