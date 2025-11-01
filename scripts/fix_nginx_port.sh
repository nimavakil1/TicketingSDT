#!/bin/bash
# Fix nginx configuration to proxy to correct backend port (8003)
# This script updates nginx config files to point to port 8003 instead of 8002

set -e

echo "Fixing nginx configuration to use port 8003..."

# Find all nginx config files that reference port 8002
CONFIG_FILES=$(sudo grep -rl "proxy_pass http://localhost:8002" /etc/nginx/ 2>/dev/null || true)

if [ -z "$CONFIG_FILES" ]; then
    echo "No nginx config files found with port 8002. Configuration may already be correct."
    sudo nginx -T | grep -A 3 "location /api/"
    exit 0
fi

echo "Found nginx config files to update:"
echo "$CONFIG_FILES"
echo ""

# Backup and update each config file
for config_file in $CONFIG_FILES; do
    echo "Updating: $config_file"

    # Create backup
    sudo cp "$config_file" "${config_file}.backup_$(date +%Y%m%d_%H%M%S)"

    # Replace port 8002 with 8003
    sudo sed -i 's/proxy_pass http:\/\/localhost:8002/proxy_pass http:\/\/localhost:8003/g' "$config_file"

    echo "✓ Updated $config_file"
done

echo ""
echo "Testing nginx configuration..."
if sudo nginx -t; then
    echo "✓ Nginx configuration test passed"
    echo ""
    echo "Reloading nginx..."
    sudo systemctl reload nginx
    echo "✓ Nginx reloaded successfully"
    echo ""
    echo "Verifying new configuration:"
    sudo nginx -T 2>/dev/null | grep -A 3 "location /api/"
    echo ""
    echo "✓ Nginx is now proxying /api/ requests to port 8003"
    echo ""
    echo "⚠️  IMPORTANT: Clear your browser cache or hard refresh (Ctrl+Shift+R) before logging in"
else
    echo "✗ Nginx configuration test failed"
    echo "Restoring backups..."
    for config_file in $CONFIG_FILES; do
        BACKUP=$(ls -t "${config_file}.backup_"* 2>/dev/null | head -1)
        if [ -n "$BACKUP" ]; then
            sudo cp "$BACKUP" "$config_file"
            echo "Restored: $config_file"
        fi
    done
    exit 1
fi
