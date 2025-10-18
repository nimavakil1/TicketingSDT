#!/usr/bin/env python3
"""
Database migration script for message system
Adds new tables and columns for pending message functionality
"""

import sqlite3
import sys
from pathlib import Path

def migrate_database(db_path: str):
    """Apply migration to add message system tables and columns"""

    print(f"Migrating database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if migration already applied
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pending_messages'")
        if cursor.fetchone():
            print("✓ Migration already applied - pending_messages table exists")
            return

        print("Starting migration...")

        # Step 1: Add new columns to ticket_states table
        print("1. Adding new columns to ticket_states...")

        # Check if columns exist before adding
        cursor.execute("PRAGMA table_info(ticket_states)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        if 'supplier_email' not in existing_columns:
            cursor.execute("""
                ALTER TABLE ticket_states
                ADD COLUMN supplier_email VARCHAR(255)
            """)
            print("   ✓ Added supplier_email column")

        if 'supplier_ticket_references' not in existing_columns:
            cursor.execute("""
                ALTER TABLE ticket_states
                ADD COLUMN supplier_ticket_references TEXT
            """)
            print("   ✓ Added supplier_ticket_references column")

        if 'purchase_order_number' not in existing_columns:
            cursor.execute("""
                ALTER TABLE ticket_states
                ADD COLUMN purchase_order_number VARCHAR(50)
            """)
            print("   ✓ Added purchase_order_number column")

            # Add index on purchase_order_number
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS ix_ticket_states_purchase_order_number
                ON ticket_states(purchase_order_number)
            """)
            print("   ✓ Added index on purchase_order_number")

        # Step 2: Create message_templates table
        print("2. Creating message_templates table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS message_templates (
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
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS ix_message_templates_template_id
            ON message_templates(template_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS ix_message_templates_recipient_type
            ON message_templates(recipient_type)
        """)

        print("   ✓ Created message_templates table with indexes")

        # Step 3: Create pending_messages table
        print("3. Creating pending_messages table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pending_messages (
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
                FOREIGN KEY (ai_decision_id) REFERENCES ai_decision_logs(id),
                FOREIGN KEY (reviewed_by) REFERENCES users(id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS ix_pending_messages_ticket_id
            ON pending_messages(ticket_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS ix_pending_messages_status
            ON pending_messages(status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS ix_pending_messages_message_type
            ON pending_messages(message_type)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS ix_pending_messages_confidence_score
            ON pending_messages(confidence_score)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS ix_pending_messages_created_at
            ON pending_messages(created_at)
        """)

        print("   ✓ Created pending_messages table with indexes")

        # Commit all changes
        conn.commit()
        print("\n✅ Migration completed successfully!")

    except sqlite3.Error as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}", file=sys.stderr)
        sys.exit(1)

    finally:
        conn.close()


def main():
    """Run migration on all database files"""

    # Find database files
    db_files = [
        "ticketing.db",
        "ticketing_agent.db",
        "data/support_agent.db"  # Backend API database
    ]

    migrated = 0
    for db_file in db_files:
        if Path(db_file).exists():
            # Check if database has ticket_states table (indicates it needs migration)
            try:
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ticket_states'")
                has_table = cursor.fetchone() is not None
                conn.close()

                if has_table:
                    migrate_database(db_file)
                    migrated += 1
                    print()
                else:
                    file_size = Path(db_file).stat().st_size
                    if file_size == 0:
                        print(f"⚠ Skipping empty database: {db_file}")
                    else:
                        print(f"⚠ Database {db_file} exists but has no ticket_states table - skipping")
            except sqlite3.Error as e:
                print(f"⚠ Error checking database {db_file}: {e}")
                continue

    if migrated == 0:
        print("⚠ No databases found to migrate. Run the application first to create the database.")
    else:
        print(f"✅ Successfully migrated {migrated} database(s)")


if __name__ == "__main__":
    main()
