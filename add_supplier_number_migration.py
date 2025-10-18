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
            # SQLite doesn't allow adding UNIQUE columns, so add without constraint first
            cursor.execute("""
                ALTER TABLE suppliers
                ADD COLUMN supplier_number INTEGER
            """)
            conn.commit()
            print("✓ Added supplier_number column")

            # Now create unique index
            print("Creating unique index on supplier_number...")
            cursor.execute("""
                CREATE UNIQUE INDEX idx_supplier_number ON suppliers(supplier_number)
            """)
            conn.commit()
            print("✓ Created unique index")
        else:
            print("✓ supplier_number column already exists")

            # Check if index exists
            cursor.execute("PRAGMA index_list(suppliers)")
            indexes = [row[1] for row in cursor.fetchall()]
            if 'idx_supplier_number' not in indexes:
                print("Creating unique index on supplier_number...")
                cursor.execute("""
                    CREATE UNIQUE INDEX idx_supplier_number ON suppliers(supplier_number)
                """)
                conn.commit()
                print("✓ Created unique index")
            else:
                print("✓ Unique index already exists")

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
