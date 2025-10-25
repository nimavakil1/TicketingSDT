# Systemd Service Installation

This guide will help you install the AI Support Agent as a systemd service, ensuring it runs automatically on boot and restarts on failure.

## Benefits

- **Auto-start on boot**: Service starts automatically when server restarts
- **Single instance**: Prevents multiple orchestrators from running
- **Auto-restart**: Automatically restarts on crashes
- **Better logging**: Integrated with systemd journal
- **Easy management**: Use standard systemctl commands

## Prerequisites

- Root/sudo access
- Orchestrator must be working when run manually

## Installation Steps

### 1. Stop any running orchestrators

```bash
cd ~/TicketingSDT
pkill -f "python3 main.py"
```

### 2. Configure error alerting (optional but recommended)

Add to your `.env` file:

```bash
# Error Alerting
ERROR_ALERTS_ENABLED=true
ERROR_ALERT_EMAIL=your-email@example.com
ERROR_ALERT_RATE_LIMIT_MINUTES=30
```

### 3. Install the service

```bash
cd ~/TicketingSDT
sudo ./install_service.sh
```

The script will:
- Copy the service file to `/etc/systemd/system/`
- Configure it for your user and home directory
- Stop any running orchestrators
- Enable the service to start on boot
- Start the service

### 4. Verify it's running

```bash
sudo systemctl status support_agent
```

You should see `Active: active (running)`.

## Service Management Commands

### Check status
```bash
sudo systemctl status support_agent
```

### View live logs
```bash
sudo journalctl -u support_agent -f
```

### View logs from specific time
```bash
# Last 100 lines
sudo journalctl -u support_agent -n 100

# Since 1 hour ago
sudo journalctl -u support_agent --since "1 hour ago"

# Today's logs
sudo journalctl -u support_agent --since today
```

### Start service
```bash
sudo systemctl start support_agent
```

### Stop service
```bash
sudo systemctl stop support_agent
```

### Restart service
```bash
sudo systemctl restart support_agent
```

### Disable auto-start
```bash
sudo systemctl disable support_agent
```

### Enable auto-start
```bash
sudo systemctl enable support_agent
```

## After Code Updates

After pulling new code from git:

```bash
cd ~/TicketingSDT
git pull origin develop

# Restart the service to use new code
sudo systemctl restart support_agent

# Watch logs to ensure it starts correctly
sudo journalctl -u support_agent -f
```

## Troubleshooting

### Service won't start

1. Check logs:
```bash
sudo journalctl -u support_agent -n 50
```

2. Verify environment variables are loaded:
```bash
cat ~/.env
```

3. Test manually first:
```bash
cd ~/TicketingSDT
./start_orchestrator.sh
```

If it works manually but not as a service, the issue is likely with the service file configuration.

### Multiple instances running

The systemd service prevents this automatically. If you see duplicates:

```bash
# Stop service
sudo systemctl stop support_agent

# Kill all instances
pkill -f "python3 main.py"

# Start service again
sudo systemctl start support_agent
```

### Service keeps restarting

Check logs for the error:
```bash
sudo journalctl -u support_agent -n 100
```

Common issues:
- Missing environment variables in `.env`
- Database permissions
- API credentials expired
- Gmail token expired

## Uninstallation

To remove the service:

```bash
# Stop and disable
sudo systemctl stop support_agent
sudo systemctl disable support_agent

# Remove service file
sudo rm /etc/systemd/system/support_agent.service

# Reload systemd
sudo systemctl daemon-reload
```

## Error Alerting

With error alerting enabled, you'll receive emails for:

- **Orchestrator crashes**: Fatal errors that stop the service
- **API failures**: Repeated failures of OpenAI, Ticketing API, or Gmail
- **Gmail auth issues**: Authentication failures
- **Database errors**: Database connection or query issues
- **Stuck emails**: Emails failing repeatedly in retry queue
- **High rejection rates**: Unusually high message rejection rates

Alerts are rate-limited (default: 30 minutes between same type) to prevent spam.

### Testing alerts

You can test the alerting system by temporarily breaking something (e.g., invalid API key) and watching for the alert email.

## Monitoring

### Health check script

Create a cron job to check if the service is running:

```bash
#!/bin/bash
# /home/ai/check_orchestrator.sh

if ! systemctl is-active --quiet support_agent; then
    echo "Orchestrator is not running!" | mail -s "Orchestrator Down" your-email@example.com
fi
```

Add to crontab:
```bash
# Check every 5 minutes
*/5 * * * * /home/ai/check_orchestrator.sh
```

## Best Practices

1. **Always use systemctl**: Don't run `python3 main.py` manually in production
2. **Check logs after restart**: Verify service started correctly
3. **Monitor error alerts**: Act on critical alerts quickly
4. **Update regularly**: Keep the service updated with `git pull` + `systemctl restart`
5. **Test before deploying**: Test changes in staging first

## Migration from nohup

If you were previously using nohup:

1. Stop all nohup processes:
```bash
pkill -f "python3 main.py"
pkill -f "start_orchestrator.sh"
```

2. Remove nohup.out if desired:
```bash
rm ~/TicketingSDT/nohup.out
```

3. Install systemd service (see Installation Steps above)

The service logs to `logs/support_agent.log` and systemd journal, not nohup.out.
