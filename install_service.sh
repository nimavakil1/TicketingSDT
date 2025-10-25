#!/bin/bash
# Install systemd service for AI Support Agent Orchestrator

set -e

echo "Installing AI Support Agent systemd service..."

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run with sudo"
    echo "Usage: sudo ./install_service.sh"
    exit 1
fi

# Get the actual user (not root)
ACTUAL_USER="${SUDO_USER:-$USER}"
USER_HOME=$(eval echo ~$ACTUAL_USER)

echo "Installing for user: $ACTUAL_USER"
echo "Home directory: $USER_HOME"

# Copy service file to systemd
echo "Copying service file to /etc/systemd/system/..."
cp support_agent.service /etc/systemd/system/

# Update service file with actual user home directory
sed -i "s|/home/ai|$USER_HOME|g" /etc/systemd/system/support_agent.service
sed -i "s|User=ai|User=$ACTUAL_USER|g" /etc/systemd/system/support_agent.service

# Create runtime directory
mkdir -p /run/support_agent
chown $ACTUAL_USER:$ACTUAL_USER /run/support_agent

# Reload systemd
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Stop any running orchestrators
echo "Stopping any running orchestrators..."
pkill -f "python3 main.py" || true
sleep 2

# Enable service to start on boot
echo "Enabling service to start on boot..."
systemctl enable support_agent.service

# Start the service
echo "Starting service..."
systemctl start support_agent.service

# Show status
echo ""
echo "Service installed successfully!"
echo ""
echo "Commands:"
echo "  sudo systemctl status support_agent   # Check status"
echo "  sudo systemctl stop support_agent     # Stop service"
echo "  sudo systemctl start support_agent    # Start service"
echo "  sudo systemctl restart support_agent  # Restart service"
echo "  sudo journalctl -u support_agent -f   # View live logs"
echo ""
echo "Current status:"
systemctl status support_agent --no-pager
