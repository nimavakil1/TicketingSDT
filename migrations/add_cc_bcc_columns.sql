-- Migration: Add CC and BCC email columns to pending_messages table
-- Date: 2025-11-02
-- Description: Adds cc_emails and bcc_emails columns to support To/CC/BCC field editing

-- Add cc_emails column if it doesn't exist
ALTER TABLE pending_messages ADD COLUMN cc_emails TEXT;

-- Add bcc_emails column if it doesn't exist
ALTER TABLE pending_messages ADD COLUMN bcc_emails TEXT;
