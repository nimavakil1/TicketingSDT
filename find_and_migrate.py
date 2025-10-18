#!/usr/bin/env python3
"""
Find the database file and run migration
"""
import os
import sys
import sqlite3
from pathlib import Path

def find_database():
    """Find the database file created by the application"""

    # Check common locations
    possible_paths = [
        "data/support_agent.db",
        "./data/support_agent.db",
        "../data/support_agent.db",
        "support_agent.db",
        "./support_agent.db",
    ]

    print("Searching for database file...")
    for path in possible_paths:
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"Found: {path} ({size} bytes)")
            if size > 0:
                return path

    # Search in current directory tree
    print("\nSearching current directory tree...")
    for root, dirs, files in os.walk(".", maxdepth=3):
        for file in files:
            if file.endswith(".db"):
                full_path = os.path.join(root, file)
                size = os.path.getsize(full_path)
                print(f"Found: {full_path} ({size} bytes)")

                # Check if it has ticket_states table
                try:
                    conn = sqlite3.connect(full_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ticket_states'")
                    has_table = cursor.fetchone() is not None
                    conn.close()
                    if has_table:
                        return full_path
                except:
                    pass

    return None

def check_migration_needed(db_path):
    """Check if migration is needed"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check for pending_messages table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pending_messages'")
    if cursor.fetchone():
        print("✓ Migration already applied (pending_messages table exists)")
        conn.close()
        return False

    # Check for new columns
    cursor.execute("PRAGMA table_info(ticket_states)")
    columns = {row[1] for row in cursor.fetchall()}
    conn.close()

    missing = []
    if 'supplier_email' not in columns:
        missing.append('supplier_email')
    if 'supplier_ticket_references' not in columns:
        missing.append('supplier_ticket_references')
    if 'purchase_order_number' not in columns:
        missing.append('purchase_order_number')

    if missing:
        print(f"⚠ Migration needed - missing columns: {', '.join(missing)}")
        return True

    print("⚠ Migration needed - missing tables")
    return True

def main():
    print("=== Database Migration Helper ===\n")

    db_path = find_database()

    if not db_path:
        print("\n❌ No database file found!")
        print("\nThe database should be created when you start the server.")
        print("Make sure you're in the correct directory (~/TicketingSDT)")
        print("\nTry:")
        print("  cd ~/TicketingSDT")
        print("  ls -la data/")
        sys.exit(1)

    print(f"\n✓ Found database: {db_path}")

    if not check_migration_needed(db_path):
        sys.exit(0)

    print(f"\nRunning migration on: {db_path}")

    # Import and run migration
    import migrate_message_system
    migrate_message_system.migrate_database(db_path)

    print("\n✅ Migration complete!")

if __name__ == "__main__":
    main()
