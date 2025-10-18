# Database Migration Guide - Message System

## Overview

This migration adds the message sending system to the ticketing platform, including:
- Pending message approval workflow
- Message templates
- Supplier/customer/internal message handling
- Confidence scoring
- CC management

## Changes

### New Tables

1. **`message_templates`**
   - Stores reusable message templates
   - Fields: template_id, name, recipient_type, language, subject/body templates, variables, use_cases

2. **`pending_messages`**
   - Stores AI-generated messages awaiting human approval
   - Fields: ticket_id, message_type, recipient, subject, body, attachments, confidence_score, status, retry_count

### Modified Tables

**`ticket_states`** - Added columns:
- `supplier_email` - Supplier contact email address
- `supplier_ticket_references` - Comma-separated list of supplier ticket IDs
- `purchase_order_number` - PO number for supplier communication (indexed)

## Migration Methods

### Method 1: Automatic Migration (Recommended for New Databases)

When you start the application, SQLAlchemy will automatically create all tables using `Base.metadata.create_all()`.

**Steps:**
1. Ensure the application is stopped
2. Start the API server: `uvicorn src.api.web_api:app --reload`
3. Tables will be created automatically on first startup

### Method 2: Manual Migration Script (For Existing Databases)

Use this method if you already have data in your database.

**Steps:**

1. **Backup your database** (IMPORTANT!)
   ```bash
   cp ticketing_agent.db ticketing_agent.db.backup
   ```

2. **Run the migration script:**
   ```bash
   python3 migrate_message_system.py
   ```

3. **Verify migration:**
   ```bash
   sqlite3 ticketing_agent.db ".schema pending_messages"
   sqlite3 ticketing_agent.db ".schema message_templates"
   sqlite3 ticketing_agent.db "PRAGMA table_info(ticket_states);"
   ```

### Method 3: Using SQLite CLI (Manual)

```bash
sqlite3 ticketing_agent.db

-- Add columns to ticket_states
ALTER TABLE ticket_states ADD COLUMN supplier_email VARCHAR(255);
ALTER TABLE ticket_states ADD COLUMN supplier_ticket_references TEXT;
ALTER TABLE ticket_states ADD COLUMN purchase_order_number VARCHAR(50);
CREATE INDEX ix_ticket_states_purchase_order_number ON ticket_states(purchase_order_number);

-- Create message_templates table
CREATE TABLE message_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    recipient_type VARCHAR(20) NOT NULL,
    language VARCHAR(10) NOT NULL,
    subject_template TEXT NOT NULL,
    body_template TEXT NOT NULL,
    variables TEXT,
    use_cases TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_message_templates_template_id ON message_templates(template_id);
CREATE INDEX ix_message_templates_recipient_type ON message_templates(recipient_type);

-- Create pending_messages table
CREATE TABLE pending_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL,
    message_type VARCHAR(20) NOT NULL,
    recipient_email VARCHAR(255),
    cc_emails TEXT,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    attachments TEXT,
    confidence_score REAL,
    ai_decision_id INTEGER,
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    retry_count INTEGER DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,
    reviewed_by INTEGER,
    sent_at TIMESTAMP,
    FOREIGN KEY (ticket_id) REFERENCES ticket_states(id),
    FOREIGN KEY (ai_decision_id) REFERENCES ai_decision_log(id),
    FOREIGN KEY (reviewed_by) REFERENCES users(id)
);

CREATE INDEX ix_pending_messages_ticket_id ON pending_messages(ticket_id);
CREATE INDEX ix_pending_messages_status ON pending_messages(status);
CREATE INDEX ix_pending_messages_message_type ON pending_messages(message_type);
CREATE INDEX ix_pending_messages_confidence_score ON pending_messages(confidence_score);
CREATE INDEX ix_pending_messages_created_at ON pending_messages(created_at);
```

## Verification

After migration, verify the schema:

```bash
# Check if tables exist
sqlite3 ticketing_agent.db "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"

# Check pending_messages structure
sqlite3 ticketing_agent.db ".schema pending_messages"

# Check new columns in ticket_states
sqlite3 ticketing_agent.db "PRAGMA table_info(ticket_states);" | grep -E "supplier|purchase"

# Verify indexes
sqlite3 ticketing_agent.db "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE '%message%';"
```

## Rollback

To rollback the migration:

```bash
# Restore from backup
cp ticketing_agent.db.backup ticketing_agent.db

# Or manually drop tables and columns (SQLite doesn't support DROP COLUMN easily)
sqlite3 ticketing_agent.db "DROP TABLE IF EXISTS pending_messages;"
sqlite3 ticketing_agent.db "DROP TABLE IF EXISTS message_templates;"
```

**Note:** SQLite doesn't support `ALTER TABLE DROP COLUMN`. To remove columns from `ticket_states`, you would need to:
1. Create a new table without those columns
2. Copy data from old table
3. Drop old table
4. Rename new table

## Testing

After migration, test the system:

1. **Start the API server:**
   ```bash
   uvicorn src.api.web_api:app --reload --port 8003
   ```

2. **Check API endpoints:**
   ```bash
   curl http://localhost:8003/api/messages/pending
   curl http://localhost:8003/api/messages/pending/count
   ```

3. **Verify frontend:**
   - Navigate to http://localhost:3002/messages
   - Check dashboard shows pending message count

## Troubleshooting

### Migration script fails with "table already exists"
- Migration already applied, no action needed

### Foreign key constraint errors
- Ensure `ticket_states`, `ai_decision_log`, and `users` tables exist before running migration

### Empty database warning
- This is normal for fresh installations
- Tables will be created when application starts

## Production Deployment

1. **Schedule maintenance window**
2. **Backup production database**
3. **Run migration script**
4. **Verify migration success**
5. **Deploy updated application code**
6. **Monitor logs for errors**

## Support

If you encounter issues:
1. Check the migration script output
2. Verify SQLite version: `sqlite3 --version` (requires 3.8+)
3. Review application logs: `tail -f logs/app.log`
