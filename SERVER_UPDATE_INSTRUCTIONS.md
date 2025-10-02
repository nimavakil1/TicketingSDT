# Server Update Instructions - v1.0.1

## Quick Update (For Your Server)

### Step 1: Pull the Latest Code

```bash
# Navigate to your project directory
cd /path/to/ai-support-agent

# Pull the latest changes
git pull origin master
```

Expected output:
```
remote: Enumerating objects: 15, done.
remote: Counting objects: 100% (15/15), done.
...
Updating e97002b..76e24ce
Fast-forward
 .env.example              |   2 +-
 BUGFIXES.md               | 287 +++++++++++++++++++++++++++++++++++
 CHANGELOG.md              | 184 ++++++++++++++++++++++
 DEPLOYMENT_UPDATE.md      | 234 +++++++++++++++++++++++++++
 INDEX.md                  |  12 +-
 README.md                 |   6 +
 UPDATE_SUMMARY.txt        |  89 +++++++++++
 config/settings.py        |  58 ++++---
 test_config.py            |  42 +++++
 troubleshoot.sh           | 156 ++++++++++++++++++
 10 files changed, 1024 insertions(+), 18 deletions(-)
```

### Step 2: Test Configuration

```bash
# Activate virtual environment if not already active
source venv/bin/activate

# Test that configuration loads correctly
python test_config.py
```

Expected output:
```
Testing configuration loading...

✅ Configuration loaded successfully!

Current settings:
  AI Provider: openai
  AI Model: gpt-4
  Deployment Phase: 1 (type: int)
  Confidence Threshold: 0.75
  ...

✅ All type validations passed!
```

### Step 3: Restart the Service

```bash
sudo systemctl restart ai-support-agent
```

### Step 4: Verify It's Running

```bash
# Check service status
sudo systemctl status ai-support-agent
```

Should show: **active (running)**

```bash
# Watch the logs
tail -f logs/support_agent.log
```

Should see:
```
{"event": "AI Support Agent Starting", ...}
{"event": "Orchestrator initialized", "phase": 1, ...}
{"event": "Checking for new emails", ...}
```

## What Changed?

### The Fix
Fixed a critical bug where environment variables (loaded as strings) caused Pydantic validation errors. The application would fail to start with:
```
Input should be 1, 2 or 3 [type=literal_error, input_value='1', input_type=str]
```

### Files Modified
- `config/settings.py` - Fixed type conversion for env vars
- `.env.example` - Added clarifying comments
- `README.md` - Added version info
- `INDEX.md` - Updated file list

### New Files
- `test_config.py` - Configuration test script
- `troubleshoot.sh` - Diagnostic helper
- `BUGFIXES.md` - Technical documentation
- `DEPLOYMENT_UPDATE.md` - Update guide
- `CHANGELOG.md` - Version history
- `UPDATE_SUMMARY.txt` - Quick reference

## Important Notes

✅ **Your `.env` file does NOT need changes**
- All existing configurations work as-is
- Numeric values (quoted or unquoted) are handled correctly

✅ **100% Backward Compatible**
- No breaking changes
- No database migrations needed
- No configuration syntax changes

✅ **Safe to Update**
- Simple git pull and restart
- Takes ~30 seconds
- Can rollback easily if needed

## Troubleshooting

If you encounter any issues after updating:

### 1. Run the Diagnostic Script
```bash
./troubleshoot.sh
```

This will check:
- Python version
- Virtual environment
- Configuration files
- Service status
- Database
- Logs

### 2. Check Logs
```bash
# Application logs
tail -f logs/support_agent.log

# Service logs
sudo journalctl -u ai-support-agent -n 50
```

### 3. Test Configuration Manually
```bash
python test_config.py
```

### 4. Verify Settings
```bash
python -c "from config.settings import settings; print(f'Phase: {settings.deployment_phase}'); print(f'Provider: {settings.ai_provider}')"
```

## Rollback (If Needed)

If you need to rollback to v1.0.0:

```bash
# Stop the service
sudo systemctl stop ai-support-agent

# Checkout previous version
git checkout v1.0.0

# Restart service
sudo systemctl start ai-support-agent
```

## Verification Checklist

After updating, verify:

- [ ] `git pull` completed successfully
- [ ] `python test_config.py` shows ✅ All checks passed
- [ ] Service is running: `sudo systemctl status ai-support-agent`
- [ ] Logs show no errors: `tail logs/support_agent.log`
- [ ] Can send test email and it processes correctly

## Common Issues

### Issue: "No module named 'pydantic'"
**Solution:**
```bash
source venv/bin/activate
pip install --upgrade -r requirements.txt
sudo systemctl restart ai-support-agent
```

### Issue: "Permission denied" on scripts
**Solution:**
```bash
chmod +x test_config.py troubleshoot.sh
```

### Issue: Service won't start
**Solution:**
```bash
# Check what's wrong
sudo journalctl -u ai-support-agent -n 50

# Try running manually to see error
source venv/bin/activate
python main.py
```

## Support

If you still have issues:

1. **Documentation**:
   - [BUGFIXES.md](BUGFIXES.md) - Technical details
   - [DEPLOYMENT_UPDATE.md](DEPLOYMENT_UPDATE.md) - Full guide
   - [CHANGELOG.md](CHANGELOG.md) - What changed

2. **Diagnostic Tools**:
   - Run: `./troubleshoot.sh`
   - Run: `python test_config.py`

3. **Logs**:
   - Check: `logs/support_agent.log`
   - Check: `sudo journalctl -u ai-support-agent`

## Success!

Once you see these, you're good:

```bash
$ sudo systemctl status ai-support-agent
● ai-support-agent.service - AI Customer Support Agent
   Loaded: loaded
   Active: active (running) since ...

$ tail logs/support_agent.log
{"event": "AI Support Agent Starting", "level": "info", ...}
{"event": "Orchestrator initialized", "phase": 1, "ai_provider": "openai", ...}
{"event": "Checking for new emails", "level": "info", ...}
```

---

## Quick Commands Summary

```bash
# Update
cd /path/to/ai-support-agent
git pull origin master

# Test
source venv/bin/activate
python test_config.py

# Restart
sudo systemctl restart ai-support-agent

# Verify
sudo systemctl status ai-support-agent
tail -f logs/support_agent.log

# Troubleshoot (if needed)
./troubleshoot.sh
```

---

**Version**: v1.0.1
**Date**: October 2, 2025
**GitHub**: https://github.com/nimavakil1/TicketingSDT
**Tags**: v1.0.0 (initial), v1.0.1 (bug fix)

🚀 **Ready to update!**
