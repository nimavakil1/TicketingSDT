#!/usr/bin/env python3
"""
Migration: Add supplier_number to suppliers table
"""

import sqlite3
import sys
from pathlib import Path

def run_migration(db_path: str):
    """Add supplier_number column to suppliers table"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if supplier_number column exists
        cursor.execute("PRAGMA table_info(suppliers)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'supplier_number' not in columns:
            print("Adding supplier_number column to suppliers table...")
            cursor.execute("""
                ALTER TABLE suppliers
                ADD COLUMN supplier_number INTEGER UNIQUE
            """)
            conn.commit()
            print("✓ Added supplier_number column")
        else:
            print("✓ supplier_number column already exists")

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
