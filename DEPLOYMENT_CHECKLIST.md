# Deployment Checklist

## Version Control Strategy

**VERSION: 1.0**
**CREATED: 2025-10-31**

## Purpose
This checklist prevents regressions by ensuring code and prompts stay synchronized.

---

## Pre-Deployment Checklist

### 1. Code Changes
- [ ] All Python files pass `python3 -m py_compile`
- [ ] Git commit includes clear description of changes
- [ ] Version numbers updated if applicable

### 2. Prompt Changes
When modifying `config/prompt/agent_prompt.md`:
- [ ] **Update VERSION number** at top of file
- [ ] **Update LAST UPDATED date**
- [ ] **Update CHANGES log** with brief description
- [ ] Verify examples match current code behavior
- [ ] Check greeting/signature requirements match code

### 3. Code-Prompt Synchronization
**CRITICAL:** After any formatter code changes, verify prompt alignment:

| Code Component | Prompt Section | Check |
|---|---|---|
| `message_formatter.py::_build_customer_body()` | "Body Content Rules" | Greeting/signature instructions match |
| `message_formatter.py::_build_supplier_body()` | "Example Supplier Draft" | Format matches code output |
| `message_service.py::create_pending_message()` | "Message Formatting Requirements" | PO number, references included |
| `orchestrator.py::_is_amazon_return_authorization()` | Special handling sections | New email types documented |

### 4. Testing Before Deployment
- [ ] Check recent pending messages in UI for correct format
- [ ] Verify no language mixing in drafts
- [ ] Confirm PO numbers appear in supplier messages
- [ ] Validate greetings/signatures present

---

## Deployment Steps

### Server Deployment
```bash
cd ~/TicketingSDT
git pull origin master
sudo systemctl restart support_agent_orchestrator.service
sudo systemctl status support_agent_orchestrator.service
```

### Post-Deployment Verification
- [ ] Service status shows "active (running)"
- [ ] Check logs for errors: `tail -f ~/TicketingSDT/logs/support_agent.log`
- [ ] Monitor next 2-3 generated messages for correct format
- [ ] Verify prompt version in logs (if version logging added)

---

## Common Regression Scenarios

### Symptom: Missing greetings/signatures
**Root Cause:** Prompt says "DO NOT include" but code doesn't add them
**Fix:** Update prompt to say "ALWAYS include"
**Prevention:** Check "Code-Prompt Synchronization" table above

### Symptom: Language mixing
**Root Cause:** Formatter prepending English text before AI's message
**Fix:** Remove prepending logic, let AI generate complete message
**Prevention:** Update prompt examples to show complete messages

### Symptom: Missing PO numbers
**Root Cause:** PO extraction looks in wrong field
**Fix:** Check enriched data first (ticket_state.purchase_order_number)
**Prevention:** Document field naming in code comments

### Symptom: Missing photo requests
**Root Cause:** Prompt doesn't instruct AI to request photos
**Fix:** Add "CRITICAL: Photo Requirements" section to prompt
**Prevention:** Add business logic checks to code

---

## File Versioning Guidelines

### Prompt Files
**Location:** `config/prompt/agent_prompt.md`
**Format:**
```markdown
SYSTEM PROMPT — Title
VERSION: X.Y
LAST UPDATED: YYYY-MM-DD
CHANGES: Brief description
```

**Version Numbering:**
- Major (X): Breaking changes, complete rewrite
- Minor (Y): New features, significant updates
- Update CHANGES log with each modification

### Code Files
**Use git commits with:**
- Clear subject line
- Detailed body explaining why (not just what)
- Reference related prompt changes

---

## Rollback Procedure

If deployment causes issues:

1. **Immediate Rollback:**
   ```bash
   cd ~/TicketingSDT
   git log --oneline -5  # Find last good commit
   git checkout <commit-hash>
   sudo systemctl restart support_agent_orchestrator.service
   ```

2. **Identify Issue:**
   - Check service logs
   - Compare prompt version with code
   - Review recent pending messages

3. **Fix Forward:**
   - Create fix commit
   - Update this checklist if needed
   - Deploy fix with full checklist

---

## Emergency Contacts

**For deployment issues:**
- Check GitHub issues: https://github.com/nimavakil1/TicketingSDT/issues
- Review commit history for similar fixes

---

## Maintenance Schedule

**Weekly:**
- [ ] Review prompt version vs code version
- [ ] Check for any language mixing in past week
- [ ] Verify PO numbers in supplier messages

**Monthly:**
- [ ] Review and update this checklist
- [ ] Check for new business rules to add to prompt
- [ ] Update examples in prompt if format changed

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-10-31 | Initial checklist created |

---

**Remember:** When code behavior changes, prompt MUST change too!
