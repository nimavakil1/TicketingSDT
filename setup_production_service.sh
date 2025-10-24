#!/bin/bash
# Production systemd service setup script

set -e  # Exit on error

echo "=== Setting up Production systemd Service ==="

# Check if already running
echo "Checking for existing processes..."
EXISTING=$(ps aux | grep -E '(uvicorn|python.*web_api)' | grep -v grep || true)
if [ ! -z "$EXISTING" ]; then
    echo "Found existing processes:"
    echo "$EXISTING"
    echo ""
    read -p "Kill existing processes? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pkill -f "uvicorn.*web_api" || true
        sleep 2
        echo "✓ Killed existing processes"
    fi
fi

# Create production systemd service
echo "Creating production systemd service..."
sudo tee /etc/systemd/system/support_agent.service > /dev/null <<EOF
[Unit]
Description=Support Agent Production (Port 8002)
After=network.target

[Service]
Type=simple
User=ai
WorkingDirectory=/home/ai/TicketingSDT
Environment="PATH=/home/ai/TicketingSDT/venv/bin"
Environment="DATABASE_URL=sqlite:///./data/support_agent.db"
ExecStart=/home/ai/TicketingSDT/venv/bin/uvicorn src.api.web_api:app --host 0.0.0.0 --port 8002
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable support_agent
sudo systemctl start support_agent
echo "✓ Production service created and started"

echo ""
echo "=== Setup Complete ==="
echo "Production is running on port 8002"
echo ""
echo "Commands:"
echo "  Status:  sudo systemctl status support_agent"
echo "  Logs:    sudo journalctl -u support_agent -f"
echo "  Restart: sudo systemctl restart support_agent"
echo "  Stop:    sudo systemctl stop support_agent"
echo ""
sudo systemctl status support_agent --no-pager
