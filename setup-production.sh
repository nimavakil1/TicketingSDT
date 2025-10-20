#!/bin/bash
# One-time setup script to switch nginx from dev mode to production mode
# Run with: sudo ./setup-production.sh

set -e

NGINX_CONFIG="/etc/nginx/sites-available/ai-agent"

echo "🔧 Configuring nginx for production mode..."

# Backup original config
cp "$NGINX_CONFIG" "${NGINX_CONFIG}.backup.$(date +%Y%m%d-%H%M%S)"

# Replace proxy_pass lines with production config
sed -i '
/proxy_pass http:\/\/localhost:3002/,/proxy_set_header X-Forwarded-Proto/ {
    s/^[[:space:]]*proxy_pass/        # proxy_pass/
    s/^[[:space:]]*proxy_set_header/        # proxy_set_header/
}
' "$NGINX_CONFIG"

# Uncomment production config
sed -i '
s/^[[:space:]]*# root \/home\/ai\/TicketingSDT\/frontend\/dist;/        root \/home\/ai\/TicketingSDT\/frontend\/dist;/
s/^[[:space:]]*# try_files/        try_files/
' "$NGINX_CONFIG"

echo "✅ Nginx config updated"

# Test and reload nginx
echo "🧪 Testing nginx configuration..."
nginx -t

echo "🔄 Reloading nginx..."
systemctl reload nginx

echo "✅ Production mode enabled!"
echo ""
echo "Now run: cd ~/TicketingSDT && ./deploy.sh"
