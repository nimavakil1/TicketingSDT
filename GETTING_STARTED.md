# Getting Started with AI Support Agent

Quick guide to get up and running in 15 minutes.

## Prerequisites

- Python 3.11+
- Gmail account
- API key (OpenAI, Anthropic, or Gemini)
- The ticketing API credentials (provided in PDF)

## Quick Setup (Local Testing)

### 1. Install Dependencies

```bash
cd ai-support-agent
./quickstart.sh
```

The script will:
- Create virtual environment
- Install dependencies
- Check for configuration
- Initialize database
- Run tests

### 2. Configure Environment

```bash
cp .env.example .env
nano .env
```

**Minimum required settings:**

```env
# Ticketing API (already provided)
TICKETING_API_USERNAME=TicketingAgent
TICKETING_API_PASSWORD=75U4$d1GN5Ld>q8&vy)|\(82!&3W3ZH

# Gmail
GMAIL_SUPPORT_EMAIL=your-support@email.com

# AI (choose one)
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here

# Phase (start with 1)
DEPLOYMENT_PHASE=1

# Alerts
INTERNAL_ALERT_EMAIL=your-ops@email.com
```

### 3. Setup Gmail OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create project
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download JSON and save as:
   ```bash
   config/gmail_credentials.json
   ```

### 4. Run Initial Authentication

```bash
python main.py
```

First run will:
- Open authentication URL
- Ask you to authorize Gmail access
- Save token for future use
- Start monitoring

**Press Ctrl+C to stop after testing**

### 5. Send Test Email

Send an email to your support address with:
- Subject: "Test Order"
- Body: "Where is my order 123-4567890-1234567?"

Watch the logs to see it process!

## Verify It's Working

### Check Logs
```bash
tail -f logs/support_agent.log
```

You should see:
```
✓ AI Support Agent Starting
✓ Orchestrator initialized
✓ Checking for new emails
✓ Found unprocessed messages
✓ Processing email
✓ AI analysis complete
✓ Action dispatched
```

### Check Database
```bash
sqlite3 data/support_agent.db

-- See processed emails
SELECT * FROM processed_emails;

-- See AI decisions
SELECT * FROM ai_decision_logs;

-- Exit
.quit
```

### Check Ticketing System
- Log into your ticketing system
- Find the ticket by order number
- Look for internal note (Phase 1) or customer reply (Phase 2+)

## What Happens in Each Phase?

### Phase 1 (Shadow Mode) - **START HERE**
✅ AI reads emails
✅ AI analyzes intent
✅ AI generates response
❌ **Does NOT send to customer**
✅ Posts suggestion as internal note

**Perfect for testing and validation!**

### Phase 2 (Partial Automation)
✅ AI reads emails
✅ AI analyzes intent
✅ AI generates response
✅ **SENDS to customer if confidence > threshold**
❌ Escalates if uncertain

**Use after Phase 1 validation (1-2 weeks)**

### Phase 3 (Full Automation)
✅ Handles everything automatically
✅ Only escalates complex cases
✅ Human focuses on escalations only

**Use after Phase 2 is stable**

## Common First-Time Issues

### "Gmail credentials not found"
→ Download OAuth credentials from Google Cloud Console
→ Save as `config/gmail_credentials.json`

### "OPENAI_API_KEY not set"
→ Add to `.env` file:
```env
OPENAI_API_KEY=sk-your-key-here
```

### "Authentication failed"
→ Check ticketing API credentials in `.env`
→ Verify they match the provided credentials

### "No new messages found"
→ Send a test email to your support address
→ Wait 60 seconds for poll cycle
→ Check it's not already labeled

### "Permission denied"
→ Make scripts executable:
```bash
chmod +x quickstart.sh main.py manage_suppliers.py
```

## Adding Suppliers

```bash
# Activate virtual environment
source venv/bin/activate

# Add a supplier
python manage_suppliers.py add "Supplier Name" "default@supplier.com"

# Add contact fields
python manage_suppliers.py add-contact 1 returns returns@supplier.com
python manage_suppliers.py add-contact 1 tracking tracking@supplier.com

# List all suppliers
python manage_suppliers.py list
```

## Testing Different Scenarios

### Test Tracking Inquiry (German)
```
Subject: Wo ist meine Bestellung?
Body: Ich habe Bestellung 123-4567890-1234567 vor einer Woche aufgegeben. Wo ist sie?
```

### Test Return Request (English)
```
Subject: Return Request
Body: I want to return my order 123-4567890-1234567. The item is damaged.
```

### Test Price Question (French)
```
Subject: Question sur le prix
Body: J'ai une question sur le prix de ma commande 123-4567890-1234567.
```

## Monitoring

### Watch Logs
```bash
# Real-time logs
tail -f logs/support_agent.log

# Filter for errors
grep ERROR logs/support_agent.log

# Filter for specific order
grep "123-4567890-1234567" logs/support_agent.log
```

### Check Status
```bash
# If running as service
sudo systemctl status ai-support-agent

# View recent service logs
sudo journalctl -u ai-support-agent -n 50
```

### Database Queries
```bash
sqlite3 data/support_agent.db

-- Today's processed emails
SELECT COUNT(*) FROM processed_emails
WHERE DATE(processed_at) = DATE('now');

-- Recent AI confidence scores
SELECT confidence_score, detected_intent
FROM ai_decision_logs
ORDER BY created_at DESC LIMIT 10;

-- Escalated tickets
SELECT ticket_number, escalation_reason
FROM ticket_states
WHERE escalated = 1;
```

## Stopping the Agent

### If running in terminal:
```bash
Ctrl+C
```

### If running as service:
```bash
sudo systemctl stop ai-support-agent
```

## Next Steps

1. ✅ **Run Phase 1 for 1-2 weeks**
   - Review AI suggestions daily
   - Compare with human responses
   - Track accuracy

2. ✅ **Evaluate Performance**
   - Check confidence scores
   - Review escalation reasons
   - Gather team feedback

3. ✅ **Progress to Phase 2**
   - Update `.env`: `DEPLOYMENT_PHASE=2`
   - Set confidence threshold: `CONFIDENCE_THRESHOLD=0.80`
   - Monitor closely

4. ✅ **Optimize**
   - Adjust confidence threshold
   - Refine supplier contacts
   - Update AI model if needed

5. ✅ **Eventually Phase 3**
   - Full automation
   - Focus on escalations only

## Getting Help

### Documentation
- **README.md** - Complete user guide
- **SETUP_GUIDE.md** - Detailed VPS deployment
- **ARCHITECTURE.md** - Technical details
- **PROJECT_SUMMARY.md** - Overview

### Debugging
```bash
# Test individual components
python -c "from src.api.ticketing_client import TicketingAPIClient; c = TicketingAPIClient(); print('API OK')"

python -c "from src.ai.ai_engine import AIEngine; e = AIEngine(); print('AI OK')"

python -c "from src.email.gmail_monitor import GmailMonitor; m = GmailMonitor(); print('Gmail OK')"
```

### Check Configuration
```bash
# View current settings (hides secrets)
python -c "from config.settings import settings; print(f'Phase: {settings.deployment_phase}'); print(f'AI: {settings.ai_provider}'); print(f'Model: {settings.ai_model}')"
```

## Tips for Success

1. **Start with Phase 1** - Don't skip validation
2. **Monitor Daily** - Review logs and decisions
3. **Add Suppliers** - Keep contact info updated
4. **Set Realistic Thresholds** - Start with 0.80 confidence
5. **Review Escalations** - Learn from uncertain cases
6. **Keep AI Updated** - Use latest models
7. **Backup Database** - Weekly backups recommended
8. **Rotate Logs** - Set up log rotation
9. **Test Different Languages** - Verify multilingual support
10. **Gather Feedback** - Ask support team for input

## Production Deployment

Once tested locally, deploy to VPS:
1. Follow **SETUP_GUIDE.md**
2. Use SystemD service for auto-start
3. Set up log rotation
4. Configure backups
5. Monitor daily

## Quick Command Reference

```bash
# Start
python main.py

# Stop (Ctrl+C or)
sudo systemctl stop ai-support-agent

# Restart
sudo systemctl restart ai-support-agent

# View logs
tail -f logs/support_agent.log

# Check status
sudo systemctl status ai-support-agent

# Add supplier
python manage_suppliers.py add "Name" "email@domain.com"

# List suppliers
python manage_suppliers.py list

# Run tests
python -m pytest tests/ -v

# Database shell
sqlite3 data/support_agent.db
```

## You're Ready! 🚀

You now have a fully functional AI support agent. Start with Phase 1, monitor the results, and gradually progress to full automation.

**Remember**: The AI is here to help your team, not replace them. Use escalations wisely and maintain quality standards.

Good luck!
