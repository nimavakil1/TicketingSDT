#!/bin/bash
# Staging Environment Setup Script

set -e  # Exit on error

echo "=== Setting up Staging Environment ==="

# Step 1: Clone staging directory
echo "Step 1: Cloning to ~/TicketingSDT-staging..."
cd ~
if [ -d "TicketingSDT-staging" ]; then
    echo "TicketingSDT-staging already exists. Removing..."
    rm -rf TicketingSDT-staging
fi
git clone https://github.com/nimavakil1/TicketingSDT.git TicketingSDT-staging
cd TicketingSDT-staging
git checkout develop
echo "✓ Cloned and switched to develop branch"

# Step 2: Create virtual environment
echo "Step 2: Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
echo "✓ Virtual environment created"

# Step 3: Create staging database (copy from production)
echo "Step 3: Setting up staging database..."
mkdir -p data
if [ -f ~/TicketingSDT/data/support_agent.db ]; then
    cp ~/TicketingSDT/data/support_agent.db data/support_agent_staging.db
    echo "✓ Copied production database to staging"
else
    echo "⚠ Production database not found, will create new staging DB"
fi

# Step 4: Create staging systemd service
echo "Step 4: Creating staging systemd service..."
sudo tee /etc/systemd/system/support_agent_staging.service > /dev/null <<EOF
[Unit]
Description=Support Agent Staging (Port 8003)
After=network.target

[Service]
Type=simple
User=ai
WorkingDirectory=/home/ai/TicketingSDT-staging
Environment="PATH=/home/ai/TicketingSDT-staging/venv/bin"
Environment="DATABASE_URL=sqlite:///./data/support_agent_staging.db"
Environment="API_PORT=8003"
ExecStart=/home/ai/TicketingSDT-staging/venv/bin/uvicorn src.api.web_api:app --host 0.0.0.0 --port 8003
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable support_agent_staging
sudo systemctl start support_agent_staging
echo "✓ Staging service created and started"

# Step 5: Check status
echo ""
echo "=== Setup Complete ==="
echo "Staging environment is running on port 8003"
echo ""
echo "Commands:"
echo "  Status:  sudo systemctl status support_agent_staging"
echo "  Logs:    sudo journalctl -u support_agent_staging -f"
echo "  Restart: sudo systemctl restart support_agent_staging"
echo "  Stop:    sudo systemctl stop support_agent_staging"
echo ""
echo "Access staging at: http://localhost:8003"
echo ""
sudo systemctl status support_agent_staging --no-pager
