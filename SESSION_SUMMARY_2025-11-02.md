# Session Summary - November 2, 2025

## Issues Investigated & Fixed

### 1. ✅ Ticket DE25007314 Missing Messages (FIXED)
**Problem:** Ticket had no message history despite being created from an email.

**Investigation:**
- Email was processed at 16:40:31 → Created ticket DE25007315 (id=101)
- SAME email reprocessed at 17:40:02 → Created DUPLICATE ticket DE25007314 (id=102)
- First ticket got the email history, second ticket was empty

**Root Cause:** Missing idempotency check - emails could be processed multiple times.

**Fix Applied:** Added idempotency check in `_process_single_email()` (orchestrator.py:319-334)
- Checks `processed_emails` table for `gmail_message_id` before processing
- Skips already-processed emails
- Commit: `07859f4`

### 2. ✅ Ticket ID vs Ticket NUMBER Bug (FIXED)
**Problem:** After creating tickets via UpsertTicket API, Step 4 always failed to find them, resulting in 0 successful ticket creations.

**Root Cause:**
- UpsertTicket returns **ticket ID** (e.g., "2476") in `serviceResult` field
- Code was calling `get_ticket_by_id()` with this ID
- Newly created tickets aren't immediately available via ID endpoint (indexing delay)
- Variable was misleadingly named `ticket_number` when it contained `ticket_id`

**Fix Applied:** Changed Step 4 to search by order number instead
- Uses `get_ticket_by_amazon_order_number()` which queries search index
- Falls back to `get_ticket_by_id()` only if no order number available
- Updated variable names and comments for clarity
- Commit: `2948db5`

### 3. ✅ Database Migration for CC/BCC Columns (APPLIED)
**Problem:** Web API crashed on startup with error: `no such column: pending_messages.bcc_emails`

**Fix Applied:**
- Created migration: `migrations/add_cc_bcc_columns.sql`
- Added `bcc_emails TEXT` column to `pending_messages` table
- Applied migration on server
- Commit: `7b19814`

## Current System Status

### ✅ Running Services
- **Orchestrator:** PID 2909124, processing emails every 60 seconds
- **Web API:** PID 2909570, running on port 8003
- **Frontend:** Built and served via nginx at https://ai.distri-smart.com
- **Nginx:** Reloaded with latest frontend build

### ✅ Features Verified Working
- Idempotency check preventing duplicate email processing
- Email history saved even when ticket API fails (graceful degradation)
- Database migrations applied

## Pending Issues (For Next Session)

### 1. ❌ To/CC/BCC Fields Not Visible in UI

**Current Status:**
- Fields were added to `MessageDetailModal.tsx` (used on `/messages` page) ✅
- Fields are NOT in `TicketDetail.tsx` inline editor (used on `/tickets/:id` page) ❌

**What Needs to Be Done:**
Add To/CC/BCC fields to ticket detail page's pending message editor:

**File:** `frontend/src/pages/TicketDetail.tsx`

**Step 1:** Add state variables (after line 50):
```typescript
const [editedRecipientEmail, setEditedRecipientEmail] = useState('');
const [editedCcEmails, setEditedCcEmails] = useState('');
const [editedBccEmails, setEditedBccEmails] = useState('');
```

**Step 2:** Initialize when editing starts (around line 1552):
```typescript
onClick={() => {
  setEditingMessageId(msg.id);
  setEditedMessageBody(msg.body);
  setEditedMessageSubject(msg.subject || '');
  setEditedRecipientEmail(msg.recipient_email || '');
  setEditedCcEmails(msg.cc_emails ? msg.cc_emails.join(', ') : '');
  setEditedBccEmails(msg.bcc_emails ? msg.bcc_emails.join(', ') : '');
}}
```

**Step 3:** Add input fields in edit mode (after line 1463, before Message Body):
```typescript
<div>
  <label className="block text-sm font-medium text-gray-700 mb-1">
    To
  </label>
  <input
    type="email"
    value={editedRecipientEmail}
    onChange={(e) => setEditedRecipientEmail(e.target.value)}
    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
    placeholder="recipient@example.com"
  />
</div>

<div>
  <label className="block text-sm font-medium text-gray-700 mb-1">
    CC (comma-separated)
  </label>
  <input
    type="text"
    value={editedCcEmails}
    onChange={(e) => setEditedCcEmails(e.target.value)}
    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
    placeholder="email1@example.com, email2@example.com"
  />
</div>

<div>
  <label className="block text-sm font-medium text-gray-700 mb-1">
    BCC (comma-separated)
  </label>
  <input
    type="text"
    value={editedBccEmails}
    onChange={(e) => setEditedBccEmails(e.target.value)}
    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
    placeholder="email1@example.com, email2@example.com"
  />
</div>
```

**Step 4:** Update handleApproveMessage to include fields (around line 643):
```typescript
const updated_data = isEditing ? {
  body: editedMessageBody,
  subject: editedMessageSubject,
  recipient_email: editedRecipientEmail !== msg.recipient_email ? editedRecipientEmail : undefined,
  cc_emails: editedCcEmails ? editedCcEmails.split(',').map(e => e.trim()).filter(e => e) : undefined,
  bcc_emails: editedBccEmails ? editedBccEmails.split(',').map(e => e.trim()).filter(e => e) : undefined,
  attachments: editedMessageAttachments.length > 0 ? filePathsFromUpload : undefined
} : undefined;
```

**Step 5:** Clear state on cancel (around line 1526):
```typescript
setEditedRecipientEmail('');
setEditedCcEmails('');
setEditedBccEmails('');
```

### 2. ❌ Hugo Writing in English to German Customers

**Problem:** AI prompt has "ALWAYS RESPOND IN RECEIPENT LANGUAGE" (line 11) but Hugo still writes English to German customers.

**Root Cause:** Language instruction is buried in prompt and has typo ("RECEIPENT" instead of "RECIPIENT").

**Proposed Fix:** Make language instruction more prominent:

**File:** `config/prompt/agent_prompt.md`

**Change 1:** Move language instruction to top (after "Role" section, before line 12):
```markdown
⚠️ CRITICAL LANGUAGE RULE ⚠️
ALWAYS respond in the recipient's language:
- Customer draft → Use customer's language (provided as "Customer communication language")
- Supplier draft → Use supplier's language (provided as "Supplier communication language")
- If German customer writes in German → Respond in German
- If English customer writes in English → Respond in English
NEVER mix languages or respond in wrong language!
```

**Change 2:** Fix typo on line 11:
```markdown
5.    use the recipient's language and the company's signature only.
6.    ALWAYS RESPOND IN RECIPIENT LANGUAGE (not "RECEIPENT")
```

**Change 3:** Add language validation to output format to make AI check itself.

### 3. ⏳ Test Ticket Creation with Step 4 Fix

**What to Test:**
- Monitor logs for new emails that should create tickets
- Look for "Step 5: Importing newly created ticket to DB" success messages
- Verify new tickets appear in database with all data

**Commands to Monitor:**
```bash
# Watch logs
tail -f ~/TicketingSDT/nohup.out | grep -E "(Step 3|Step 4|Step 5)"

# Check ticket count
cd ~/TicketingSDT && sqlite3 data/support_agent.db 'SELECT COUNT(*) FROM ticket_states;'

# Check latest tickets
cd ~/TicketingSDT && sqlite3 data/support_agent.db 'SELECT ticket_number, created_at FROM ticket_states ORDER BY created_at DESC LIMIT 5;'
```

## Deployed Commits (In Order)

1. `39f56ff` - Add To/CC/BCC field editing (backend + MessageDetailModal.tsx)
2. `547096b` - Remove Manual Upload & Attachments section
3. `5932b51` - Fix: Save email to history even when ticket API fails
4. `07859f4` - Fix: Add idempotency check
5. `2948db5` - Fix ticket ID vs ticket NUMBER bug in Step 4
6. `7b19814` - Add database migration for CC/BCC columns

## Rollback Information

**Backup Tag:** `backup-before-20251102-0705`

**Rollback Commands:**
```bash
# Stop services
pkill -f 'python.*main.py'
pkill -f 'uvicorn.*web_api'

# Rollback code
cd ~/TicketingSDT && git reset --hard backup-before-20251102-0705

# Restart
cd ~/TicketingSDT && nohup bash start_orchestrator.sh > nohup.out 2>&1 &
cd ~/TicketingSDT && nohup venv/bin/uvicorn src.api.web_api:app --host 0.0.0.0 --port 8003 > web_api.log 2>&1 &
```

## Notes for Next Session

1. **Priority 1:** Add To/CC/BCC fields to TicketDetail.tsx (detailed instructions above)
2. **Priority 2:** Fix Hugo language issue (make instruction more prominent in prompt)
3. **Priority 3:** Test ticket creation to verify Step 4 fix works
4. **Priority 4:** Add attachment management UI (Task #1 from original requirements - deferred)

## Files Modified This Session

### Backend
- `src/orchestrator.py` - Idempotency check, Step 4 fix
- `migrations/add_cc_bcc_columns.sql` - Database migration (NEW)
- `migrations/README.md` - Migration documentation (NEW)

### Frontend
- `frontend/src/components/MessageDetailModal.tsx` - To/CC/BCC fields (ALREADY DONE)
- `frontend/src/pages/TicketDetail.tsx` - Needs To/CC/BCC fields (TODO)

### Configuration
- `config/prompt/agent_prompt.md` - Needs language instruction fix (TODO)
