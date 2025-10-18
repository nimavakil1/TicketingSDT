#!/usr/bin/env python3
"""
Migration: Add conversation summary fields to ticket_states table
"""

import sqlite3
import sys
from pathlib import Path

def run_migration(db_path: str):
    """Add conversation summary fields to ticket_states table"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check existing columns
        cursor.execute("PRAGMA table_info(ticket_states)")
        columns = [row[1] for row in cursor.fetchall()]

        fields_to_add = [
            ('customer_conversation_summary', 'TEXT'),
            ('supplier_conversation_summary', 'TEXT'),
            ('pending_customer_promises', 'TEXT'),
            ('pending_supplier_requests', 'TEXT')
        ]

        for field_name, field_type in fields_to_add:
            if field_name not in columns:
                print(f"Adding {field_name} column to ticket_states table...")
                cursor.execute(f"""
                    ALTER TABLE ticket_states
                    ADD COLUMN {field_name} {field_type}
                """)
                conn.commit()
                print(f"✓ Added {field_name} column")
            else:
                print(f"✓ {field_name} column already exists")

    except Exception as e:
        print(f"Error running migration: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    db_path = "data/support_agent.db"

    if not Path(db_path).exists():
        print(f"Error: Database file '{db_path}' not found")
        sys.exit(1)

    print(f"Running migration on {db_path}...")
    run_migration(db_path)
    print("Migration completed successfully!")
