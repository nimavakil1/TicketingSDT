# Deployment Update Instructions

## Bug Fix - Configuration Loading Issue

### What Was Fixed
The application had a Pydantic configuration validation error when loading settings from `.env` file. Environment variables were being loaded as strings, but Pydantic expected specific types (int, float).

### Files Changed
1. `config/settings.py` - Added type conversion validators
2. `.env.example` - Added clarifying comment
3. `test_config.py` - NEW: Configuration test script
4. `BUGFIXES.md` - NEW: Detailed bug fix documentation
5. `README.md` - Updated with version info

### How to Update Your Server

#### Option 1: Git Pull (Recommended)
```bash
# 1. Navigate to project directory
cd /path/to/ai-support-agent

# 2. Pull latest changes
git pull origin main

# 3. No .env changes needed! Your existing values will work

# 4. Test configuration
python test_config.py

# 5. If tests pass, restart the service
sudo systemctl restart ai-support-agent

# 6. Verify it's running
sudo systemctl status ai-support-agent
tail -f logs/support_agent.log
```

#### Option 2: Manual Update
If you can't use git pull, just replace `config/settings.py` with the new version:

```bash
# Backup current file
cp config/settings.py config/settings.py.backup

# Download new version (or copy from local)
# Then restart
sudo systemctl restart ai-support-agent
```

### Verification Steps

**1. Test configuration loading:**
```bash
python test_config.py
```

Expected output:
```
✅ Configuration loaded successfully!

Current settings:
  AI Provider: openai
  AI Model: gpt-4
  Deployment Phase: 1 (type: int)
  ...

✅ All type validations passed!
```

**2. Check service status:**
```bash
sudo systemctl status ai-support-agent
```

Should show: `active (running)`

**3. Monitor logs:**
```bash
tail -f logs/support_agent.log
```

Should see:
```
AI Support Agent Starting
Orchestrator initialized
Checking for new emails
```

### Common Issues & Solutions

#### Issue: "ModuleNotFoundError: No module named 'pydantic'"
**Solution:**
```bash
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

#### Issue: "Settings validation error"
**Solution:**
1. Check your `.env` file syntax
2. Run: `python test_config.py`
3. Look for the specific field causing issues
4. Ensure no spaces around `=` signs
5. Ensure numeric values are not quoted or use proper quotes

#### Issue: Service won't start
**Solution:**
```bash
# Check error logs
sudo journalctl -u ai-support-agent -n 50

# Test manually
cd /path/to/ai-support-agent
source venv/bin/activate
python main.py
```

### What Your .env Should Look Like

```env
# Ticketing API
TICKETING_API_USERNAME=TicketingAgent
TICKETING_API_PASSWORD=your_password_here

# Gmail
GMAIL_SUPPORT_EMAIL=support@yourcompany.com

# AI Configuration
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
AI_MODEL=gpt-4
AI_TEMPERATURE=0.7
AI_MAX_TOKENS=2000

# Phase Configuration (numbers, no quotes needed)
DEPLOYMENT_PHASE=1
CONFIDENCE_THRESHOLD=0.75

# Other settings...
```

### Rollback Instructions

If you need to rollback:

```bash
# 1. Stop service
sudo systemctl stop ai-support-agent

# 2. Restore backup
cp config/settings.py.backup config/settings.py

# 3. Start service
sudo systemctl start ai-support-agent
```

### Testing the Fix

Send a test email to your support address and verify:

1. ✅ Application starts without errors
2. ✅ Configuration loads properly
3. ✅ Email is detected and processed
4. ✅ Internal note appears in ticket (Phase 1)
5. ✅ No validation errors in logs

### Support

If you encounter issues after updating:

1. **Check logs:** `tail -f logs/support_agent.log`
2. **Test config:** `python test_config.py`
3. **Verify Python version:** `python --version` (should be 3.11+)
4. **Check dependencies:** `pip list | grep pydantic`
5. **Review BUGFIXES.md** for detailed technical information

### Quick Command Reference

```bash
# Pull updates
cd /path/to/ai-support-agent && git pull

# Test configuration
python test_config.py

# Restart service
sudo systemctl restart ai-support-agent

# Check status
sudo systemctl status ai-support-agent

# View logs
tail -f logs/support_agent.log

# View service logs
sudo journalctl -u ai-support-agent -f
```

### Summary

- ✅ **No .env changes needed** - existing values work
- ✅ **Backwards compatible** - old configurations still work
- ✅ **Simple update** - just pull and restart
- ✅ **Well tested** - includes test script
- ✅ **Safe rollback** - easy to revert if needed

---

**Version**: 1.0.1
**Update Date**: October 2, 2025
**Criticality**: Medium (fixes deployment blocker)
**Downtime Required**: ~30 seconds (service restart)
