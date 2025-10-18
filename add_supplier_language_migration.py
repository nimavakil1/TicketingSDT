#!/usr/bin/env python3
"""
Migration: Add language_code to suppliers table
"""

import sqlite3
import sys
from pathlib import Path

def run_migration(db_path: str):
    """Add language_code column to suppliers table"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(suppliers)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'language_code' not in columns:
            print("Adding language_code column to suppliers table...")
            cursor.execute("""
                ALTER TABLE suppliers
                ADD COLUMN language_code VARCHAR(10) DEFAULT 'de-DE'
            """)
            conn.commit()
            print("✓ Added language_code column")
        else:
            print("✓ language_code column already exists")

    except Exception as e:
        print(f"Error running migration: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    db_path = "ticketing.db"

    if not Path(db_path).exists():
        print(f"Error: Database file '{db_path}' not found")
        sys.exit(1)

    print(f"Running migration on {db_path}...")
    run_migration(db_path)
    print("Migration completed successfully!")
