#!/bin/bash
# Install both Web API and Orchestrator services

set -e

echo "Installing AI Support Agent services..."

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run with sudo"
    echo "Usage: sudo ./install_both_services.sh"
    exit 1
fi

# Get the actual user (not root)
ACTUAL_USER="${SUDO_USER:-$USER}"
USER_HOME=$(eval echo ~$ACTUAL_USER)

echo "Installing for user: $ACTUAL_USER"
echo "Home directory: $USER_HOME"

# Stop any existing services
echo "Stopping any existing services..."
systemctl stop support_agent 2>/dev/null || true
systemctl stop support_agent_orchestrator 2>/dev/null || true

# Kill any running orchestrators
echo "Stopping any running orchestrators..."
pkill -f "python3 main.py" || true
sleep 2

# Copy Web API service
echo "Installing Web API service..."
cp support_agent_web.service /etc/systemd/system/support_agent.service
sed -i "s|/home/ai|$USER_HOME|g" /etc/systemd/system/support_agent.service
sed -i "s|User=ai|User=$ACTUAL_USER|g" /etc/systemd/system/support_agent.service

# Copy Orchestrator service
echo "Installing Orchestrator service..."
cp support_agent_orchestrator.service /etc/systemd/system/
sed -i "s|/home/ai|$USER_HOME|g" /etc/systemd/system/support_agent_orchestrator.service
sed -i "s|User=ai|User=$ACTUAL_USER|g" /etc/systemd/system/support_agent_orchestrator.service

# Create runtime directories
mkdir -p /run/support_agent_orchestrator
chown $ACTUAL_USER:$ACTUAL_USER /run/support_agent_orchestrator

# Reload systemd
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable both services to start on boot
echo "Enabling services to start on boot..."
systemctl enable support_agent.service
systemctl enable support_agent_orchestrator.service

# Start both services
echo "Starting Web API service..."
systemctl start support_agent.service

echo "Starting Orchestrator service..."
systemctl start support_agent_orchestrator.service

# Show status
echo ""
echo "Services installed successfully!"
echo ""
echo "Web API Commands:"
echo "  sudo systemctl status support_agent"
echo "  sudo systemctl restart support_agent"
echo ""
echo "Orchestrator Commands:"
echo "  sudo systemctl status support_agent_orchestrator"
echo "  sudo systemctl restart support_agent_orchestrator"
echo "  sudo journalctl -u support_agent_orchestrator -f"
echo ""
echo "Current status:"
echo ""
echo "=== Web API ==="
systemctl status support_agent --no-pager -n 5
echo ""
echo "=== Orchestrator ==="
systemctl status support_agent_orchestrator --no-pager -n 5
