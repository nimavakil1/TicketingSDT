# Database Migration Instructions

## Issue
The database schema needs to be updated to include the message system tables and new columns on the `ticket_states` table.

## Required Changes
The migration will:
1. Add 3 new columns to `ticket_states` table:
   - `supplier_email` (VARCHAR 255)
   - `supplier_ticket_references` (TEXT)
   - `purchase_order_number` (VARCHAR 50, indexed)
2. Create `message_templates` table
3. Create `pending_messages` table

## Migration Steps

### Step 1: Start Backend to Create Database
First, you need to create the database by starting the backend server:

```bash
cd ~/TicketingSDT
source venv/bin/activate  # Activate your virtual environment
uvicorn src.api.web_api:app --host 0.0.0.0 --port 8003
```

Wait for the message: **"Application startup complete"**

Then **stop the server** with `Ctrl+C`.

### Step 2: Run Migration
Now run the migration script:

```bash
python3 migrate_message_system.py
```

Or use the helper script:

```bash
./run_migration.sh
```

### Step 3: Restart Backend
Start the backend server again:

```bash
uvicorn src.api.web_api:app --host 0.0.0.0 --port 8003
```

The server should now start without errors and the API endpoints should work correctly.

## Verification
After migration, you can verify the changes:

```bash
sqlite3 data/support_agent.db "PRAGMA table_info(ticket_states);"
sqlite3 data/support_agent.db ".tables"
```

You should see:
- The 3 new columns in `ticket_states`
- New tables: `message_templates` and `pending_messages`

## Troubleshooting

### "No databases found to migrate"
This means the database hasn't been created yet. Follow Step 1 above.

### "Migration already applied"
The migration has already run successfully. You can proceed to start the server.

### SQLite errors about missing columns
Run the migration again - it's safe to run multiple times.
