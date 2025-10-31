#!/bin/bash
# Fix sudoers file to allow Settings UI to restart orchestrator service
# This script updates /etc/sudoers.d/ticketing-backend with correct service name

set -e

echo "Updating sudoers file for ticketing-backend..."

# Create the sudoers file with correct service name
sudo tee /etc/sudoers.d/ticketing-backend > /dev/null <<'EOF'
# Allow ai user to restart ticketing services without password
ai ALL=(ALL) NOPASSWD: /bin/systemctl restart support_agent_orchestrator.service
ai ALL=(ALL) NOPASSWD: /bin/systemctl status support_agent_orchestrator.service
EOF

# Set proper permissions (very important for sudoers files!)
sudo chmod 0440 /etc/sudoers.d/ticketing-backend

echo "Sudoers file updated successfully!"
echo ""
echo "Verifying configuration:"
sudo cat /etc/sudoers.d/ticketing-backend
echo ""
echo "Testing passwordless sudo:"
if sudo -n systemctl status support_agent_orchestrator.service > /dev/null 2>&1; then
    echo "✓ Passwordless sudo is working!"
else
    echo "✗ Passwordless sudo test failed"
    exit 1
fi

echo ""
echo "✓ Settings UI restart button should now work correctly!"
