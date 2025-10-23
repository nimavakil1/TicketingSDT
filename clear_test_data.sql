-- Clear all test data while preserving configuration
-- Run this script before going live to start with a clean slate

-- Disable foreign key constraints temporarily
PRAGMA foreign_keys = OFF;

-- Clear test/operational data
DELETE FROM ticket_audit_logs;
DELETE FROM attachments;
DELETE FROM pending_messages;
DELETE FROM supplier_messages;
DELETE FROM ai_decision_logs;
DELETE FROM processed_emails;
DELETE FROM pending_email_retries;
DELETE FROM ticket_states;
DELETE FROM prompt_versions;

-- Re-enable foreign key constraints
PRAGMA foreign_keys = ON;

-- Preserve configuration tables (no changes):
-- - suppliers
-- - users
-- - system_settings (including AI system prompt)
-- - custom_statuses
-- - message_templates
-- - skip_text_blocks
-- - ignore_email_patterns

-- Verify what's left
SELECT 'Tickets remaining:', COUNT(*) FROM ticket_states;
SELECT 'AI decisions remaining:', COUNT(*) FROM ai_decision_logs;
SELECT 'Emails remaining:', COUNT(*) FROM processed_emails;
SELECT 'Pending messages remaining:', COUNT(*) FROM pending_messages;
SELECT 'Suppliers preserved:', COUNT(*) FROM suppliers;
SELECT 'Users preserved:', COUNT(*) FROM users;
SELECT 'System settings preserved:', COUNT(*) FROM system_settings;
SELECT 'Custom statuses preserved:', COUNT(*) FROM custom_statuses;
