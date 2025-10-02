# AI Support Agent - Setup Guide

Complete step-by-step guide for deploying the AI Customer Support Agent on an Ubuntu VPS.

## Prerequisites

- Ubuntu 20.04 or later
- Python 3.11+
- Root or sudo access
- Gmail account for support emails
- API keys (OpenAI, Anthropic, or Gemini)
- Ticketing system credentials (provided)

## Step 1: System Preparation

### Update system packages
```bash
sudo apt update && sudo apt upgrade -y
```

### Install Python 3.11
```bash
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev -y
```

### Install additional dependencies
```bash
sudo apt install git build-essential -y
```

## Step 2: Application Setup

### Create application directory
```bash
sudo mkdir -p /opt/ai-support-agent
sudo chown $USER:$USER /opt/ai-support-agent
cd /opt/ai-support-agent
```

### Copy application files
Upload all application files to `/opt/ai-support-agent/` or clone from repository:
```bash
# If using git
git clone <your-repo-url> .

# Or use scp to upload files
scp -r /local/ai-support-agent/* user@vps-ip:/opt/ai-support-agent/
```

### Create virtual environment
```bash
python3.11 -m venv venv
source venv/bin/activate
```

### Install Python dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Step 3: Gmail API Configuration

### On Google Cloud Console

1. Go to https://console.cloud.google.com/
2. Create a new project (e.g., "AI Support Agent")
3. Enable Gmail API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click "Enable"

4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Application type: "Desktop app"
   - Name: "AI Support Agent"
   - Download the JSON file

### On your VPS

```bash
# Create config directory
mkdir -p /opt/ai-support-agent/config

# Upload Gmail credentials
# Use scp or paste content into file
nano /opt/ai-support-agent/config/gmail_credentials.json
# Paste the downloaded JSON content
```

## Step 4: Environment Configuration

### Create .env file
```bash
cp .env.example .env
nano .env
```

### Configure required settings
```env
# Ticketing API (provided credentials)
TICKETING_API_BASE_URL=https://api.distri-smart.com/api/sdt/1
TICKETING_API_USERNAME=TicketingAgent
TICKETING_API_PASSWORD=75U4$d1GN5Ld>q8&vy)|\(82!&3W3ZH

# Gmail Configuration
GMAIL_CREDENTIALS_PATH=config/gmail_credentials.json
GMAIL_TOKEN_PATH=config/gmail_token.json
GMAIL_SUPPORT_EMAIL=support@yourcompany.com
GMAIL_PROCESSED_LABEL=AI_Agent_Processed

# AI Configuration (choose one provider)
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
AI_MODEL=gpt-4
AI_TEMPERATURE=0.7
AI_MAX_TOKENS=2000

# Phase Configuration (start with Phase 1)
DEPLOYMENT_PHASE=1
CONFIDENCE_THRESHOLD=0.75

# Database
DATABASE_URL=sqlite:///data/support_agent.db

# Default ticket owner ID
DEFAULT_OWNER_ID=1087

# Supplier reminders
SUPPLIER_REMINDER_HOURS=24
INTERNAL_ALERT_EMAIL=operations@yourcompany.com

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/support_agent.log

# Polling
EMAIL_POLL_INTERVAL_SECONDS=60
```

## Step 5: Initial Authentication

### Create necessary directories
```bash
mkdir -p /opt/ai-support-agent/data
mkdir -p /opt/ai-support-agent/logs
```

### Run initial authentication
```bash
source venv/bin/activate
python main.py
```

**Important**: This first run will open a URL in the terminal. You need to:
1. Copy the URL
2. Open it in a browser on your local machine
3. Authenticate with your Gmail account
4. Authorize the application
5. Copy the authorization code back to the terminal

After successful authentication, the application will create `config/gmail_token.json` and start running.

**For headless server**: You may need to do this initial authentication on your local machine first, then copy the `gmail_token.json` to the server.

Press `Ctrl+C` to stop after verifying it works.

## Step 6: SystemD Service Setup

### Create service file
```bash
sudo nano /etc/systemd/system/ai-support-agent.service
```

### Add service configuration
```ini
[Unit]
Description=AI Customer Support Agent
After=network.target

[Service]
Type=simple
User=<your-username>
WorkingDirectory=/opt/ai-support-agent
Environment="PATH=/opt/ai-support-agent/venv/bin"
ExecStart=/opt/ai-support-agent/venv/bin/python /opt/ai-support-agent/main.py
Restart=always
RestartSec=10
StandardOutput=append:/opt/ai-support-agent/logs/service.log
StandardError=append:/opt/ai-support-agent/logs/service-error.log

[Install]
WantedBy=multi-user.target
```

Replace `<your-username>` with your actual username.

### Enable and start service
```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-support-agent
sudo systemctl start ai-support-agent
```

### Check status
```bash
sudo systemctl status ai-support-agent
```

Should show "active (running)".

## Step 7: Verify Operation

### Check logs
```bash
tail -f /opt/ai-support-agent/logs/support_agent.log
```

You should see:
- "AI Support Agent Starting"
- "Orchestrator initialized"
- "Checking for new emails"

### Monitor service logs
```bash
sudo journalctl -u ai-support-agent -f
```

### Test with a sample email
Send a test email to your support address with an order number, then check:
```bash
# Check if email was processed
sqlite3 /opt/ai-support-agent/data/support_agent.db "SELECT * FROM processed_emails ORDER BY processed_at DESC LIMIT 1;"

# Check AI decisions
sqlite3 /opt/ai-support-agent/data/support_agent.db "SELECT * FROM ai_decision_logs ORDER BY created_at DESC LIMIT 1;"
```

## Step 8: Add Suppliers

### Using the management script
```bash
source venv/bin/activate

# Add a supplier
python manage_suppliers.py add "Supplier Name" "contact@supplier.com" \
  --contacts '{"returns": "returns@supplier.com", "tracking": "tracking@supplier.com"}'

# List suppliers
python manage_suppliers.py list

# Add contact field to existing supplier
python manage_suppliers.py add-contact 1 returns returns@supplier.com
```

## Step 9: Monitoring and Maintenance

### Daily monitoring commands
```bash
# Check service status
sudo systemctl status ai-support-agent

# View recent logs
tail -n 100 /opt/ai-support-agent/logs/support_agent.log

# Check for escalated tickets
sqlite3 /opt/ai-support-agent/data/support_agent.db "SELECT ticket_number, escalation_reason FROM ticket_states WHERE escalated = 1;"

# Check pending supplier messages
sqlite3 /opt/ai-support-agent/data/support_agent.db "SELECT COUNT(*) FROM supplier_messages WHERE response_received = 0;"
```

### Log rotation setup
```bash
sudo nano /etc/logrotate.d/ai-support-agent
```

Add:
```
/opt/ai-support-agent/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 <your-username> <your-username>
}
```

## Step 10: Phase Progression

### Phase 1 Evaluation (First 1-2 weeks)
- Monitor AI suggestions in internal notes
- Review decision logs for accuracy
- Gather feedback from support team

### Moving to Phase 2
When satisfied with Phase 1 performance:
```bash
sudo systemctl stop ai-support-agent
nano /opt/ai-support-agent/.env
# Change: DEPLOYMENT_PHASE=2
sudo systemctl start ai-support-agent
```

Monitor closely for first few days:
- Check customer responses
- Verify emails are being sent correctly
- Monitor escalation rates

### Moving to Phase 3
Only after Phase 2 is stable:
```bash
sudo systemctl stop ai-support-agent
nano /opt/ai-support-agent/.env
# Change: DEPLOYMENT_PHASE=3
sudo systemctl start ai-support-agent
```

## Troubleshooting

### Service won't start
```bash
# Check for errors
sudo journalctl -u ai-support-agent -n 50

# Test manually
cd /opt/ai-support-agent
source venv/bin/activate
python main.py
```

### Gmail authentication expired
```bash
cd /opt/ai-support-agent
rm config/gmail_token.json
source venv/bin/activate
python main.py
# Follow authentication steps again
```

### Database locked
```bash
# Check for multiple instances
ps aux | grep main.py
# Kill if found
sudo systemctl restart ai-support-agent
```

### API errors
```bash
# Test ticketing API
cd /opt/ai-support-agent
source venv/bin/activate
python -c "from src.api.ticketing_client import TicketingAPIClient; client = TicketingAPIClient(); print('OK')"

# Test AI API
python -c "from src.ai.ai_engine import AIEngine; engine = AIEngine(); print('OK')"
```

## Security Checklist

- [ ] .env file has restricted permissions: `chmod 600 .env`
- [ ] Gmail credentials protected: `chmod 600 config/gmail_*.json`
- [ ] Database protected: `chmod 600 data/*.db`
- [ ] Service running as non-root user
- [ ] Firewall configured (if needed)
- [ ] Regular backups configured for database
- [ ] API keys are valid and have usage limits set
- [ ] Logs don't contain sensitive data (review log files)

## Backup Strategy

### Automated daily backup script
```bash
nano /opt/ai-support-agent/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/opt/ai-support-agent/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
cp /opt/ai-support-agent/data/support_agent.db "$BACKUP_DIR/support_agent_$DATE.db"
find $BACKUP_DIR -name "*.db" -mtime +7 -delete
```

```bash
chmod +x /opt/ai-support-agent/backup.sh

# Add to crontab
crontab -e
# Add: 0 2 * * * /opt/ai-support-agent/backup.sh
```

## Performance Tuning

### For high email volume
```env
# Increase poll frequency (check every 30 seconds)
EMAIL_POLL_INTERVAL_SECONDS=30

# Use more efficient database (requires PostgreSQL setup)
DATABASE_URL=postgresql://user:pass@localhost/support_agent
```

### For lower AI costs
```env
# Use cheaper model
AI_MODEL=gpt-3.5-turbo

# Or use Anthropic's cheaper models
AI_PROVIDER=anthropic
AI_MODEL=claude-3-haiku-20240307
```

## Support

For issues:
1. Check logs: `/opt/ai-support-agent/logs/`
2. Review systemd logs: `sudo journalctl -u ai-support-agent`
3. Test components individually (see Troubleshooting)
4. Review database for state: `sqlite3 data/support_agent.db`

## Next Steps

1. ✅ Complete this setup
2. ✅ Run Phase 1 for 1-2 weeks
3. ✅ Evaluate AI performance
4. ✅ Gather team feedback
5. ✅ Progress to Phase 2
6. ✅ Monitor and refine
7. ✅ Eventually move to Phase 3

Good luck! 🚀
