#!/usr/bin/env python3
"""
Migration: Add to_address column to processed_emails table
"""

import sqlite3
import sys
from pathlib import Path

def run_migration(db_path: str):
    """Add to_address column to processed_emails table"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if processed_emails table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='processed_emails'")
        table_exists = cursor.fetchone()

        if not table_exists:
            print("Error: processed_emails table does not exist")
            sys.exit(1)

        # Check if to_address column exists
        cursor.execute("PRAGMA table_info(processed_emails)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'to_address' not in columns:
            print("Adding to_address column to processed_emails table...")
            cursor.execute("""
                ALTER TABLE processed_emails
                ADD COLUMN to_address VARCHAR(255)
            """)
            conn.commit()
            print("✓ Added to_address column to processed_emails table")
        else:
            print("✓ to_address column already exists")

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
