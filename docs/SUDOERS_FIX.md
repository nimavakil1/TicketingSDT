# Sudoers Fix for Settings UI Restart

## Problem

When clicking "Save Settings" in the UI, the error message appears:
```
Settings saved but service restart failed: Some services failed to restart
```

The settings are saved correctly to `.env`, but the service restart fails.

## Root Cause

The `/etc/sudoers.d/ticketing-backend` file contains old incorrect service names:
```
ai ALL=(ALL) NOPASSWD: /bin/systemctl restart ai-agent, /bin/systemctl restart ai-agent-api
```

But the actual service name is: `support_agent_orchestrator.service`

This causes the web API to fail when trying to restart the service because it doesn't have sudo permission for the correct service name.

## Solution

Update the sudoers file with the correct service name.

### Automated Fix (Recommended)

Run the provided script:

```bash
cd ~/TicketingSDT
chmod +x scripts/fix_sudoers.sh
./scripts/fix_sudoers.sh
```

### Manual Fix

If you prefer to do it manually:

```bash
# Update the sudoers file
sudo tee /etc/sudoers.d/ticketing-backend > /dev/null <<'EOF'
# Allow ai user to restart ticketing services without password
ai ALL=(ALL) NOPASSWD: /bin/systemctl restart support_agent_orchestrator.service
ai ALL=(ALL) NOPASSWD: /bin/systemctl status support_agent_orchestrator.service
EOF

# Set proper permissions (CRITICAL!)
sudo chmod 0440 /etc/sudoers.d/ticketing-backend

# Verify it works
sudo cat /etc/sudoers.d/ticketing-backend
sudo -n systemctl status support_agent_orchestrator.service
```

## Testing

After applying the fix:

1. Go to Settings page in the UI
2. Change any setting (e.g., temperature)
3. Click "Save Settings"
4. Should see: **"All services restarted successfully"**

## Security Note

This sudoers configuration:
- ✅ Only allows restarting specific service (`support_agent_orchestrator.service`)
- ✅ Only allows `status` command (read-only)
- ✅ Only for user `ai`
- ✅ No password required (safe because scope is limited)
- ❌ Does NOT allow restarting other services
- ❌ Does NOT allow other systemctl commands (stop, disable, etc.)

This is a minimal, secure configuration for the Settings UI restart functionality.
