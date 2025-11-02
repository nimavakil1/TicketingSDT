# Database Migrations

This directory contains SQL migration scripts for the support agent database.

## How to Run Migrations

From the project root directory:

```bash
sqlite3 data/support_agent.db < migrations/migration_file.sql
```

## Migration History

- **add_cc_bcc_columns.sql** (2025-11-02): Adds cc_emails and bcc_emails columns to pending_messages table for To/CC/BCC field editing support
