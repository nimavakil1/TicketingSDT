#!/usr/bin/env python3
"""
Migration script to add detailed ticket fields from ticketing system
Adds customer address, tracking info, product details, etc.
"""
import sqlite3
import sys
from pathlib import Path

def migrate_database(db_path: str):
    """Add new fields to ticket_states table"""
    print(f"\n📋 Migrating database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # List of new columns to add
    migrations = [
        # Customer details
        ("customer_address", "TEXT"),
        ("customer_city", "VARCHAR(100)"),
        ("customer_postal_code", "VARCHAR(20)"),
        ("customer_country", "VARCHAR(50)"),
        ("customer_phone", "VARCHAR(50)"),

        # Delivery/Tracking
        ("tracking_number", "VARCHAR(100)"),
        ("carrier_name", "VARCHAR(100)"),
        ("delivery_status", "VARCHAR(50)"),
        ("expected_delivery_date", "VARCHAR(50)"),

        # Product information (JSON for multiple items)
        ("product_details", "TEXT"),  # JSON: [{sku, title, quantity, price}]

        # Order details
        ("order_total", "DECIMAL(10,2)"),
        ("order_currency", "VARCHAR(10)"),
        ("order_date", "VARCHAR(50)"),

        # Supplier details (additional)
        ("supplier_phone", "VARCHAR(50)"),
        ("supplier_contact_person", "VARCHAR(255)"),
    ]

    added_count = 0
    for column_name, column_type in migrations:
        try:
            # Check if column exists
            cursor.execute(f"PRAGMA table_info(ticket_states)")
            columns = [row[1] for row in cursor.fetchall()]

            if column_name not in columns:
                print(f"  ✅ Adding column: {column_name}")
                cursor.execute(f"ALTER TABLE ticket_states ADD COLUMN {column_name} {column_type}")
                added_count += 1
            else:
                print(f"  ⏭️  Column already exists: {column_name}")
        except sqlite3.Error as e:
            print(f"  ❌ Error adding column {column_name}: {e}")
            conn.rollback()
            return False

    conn.commit()
    conn.close()

    print(f"\n✅ Migration complete! Added {added_count} new columns")
    return True

def main():
    """Run migration on all database files"""
    databases = [
        "data/support_agent.db",
        "ticketing_agent.db",
        "ticketing.db"
    ]

    success_count = 0
    for db_path in databases:
        if Path(db_path).exists():
            if Path(db_path).stat().st_size == 0:
                print(f"⚠ Skipping empty database: {db_path}")
                continue

            # Check if it has ticket_states table
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ticket_states'")
                has_table = cursor.fetchone() is not None
                conn.close()

                if has_table:
                    if migrate_database(db_path):
                        success_count += 1
                else:
                    print(f"⏭️  Skipping (no ticket_states table): {db_path}")
            except sqlite3.Error as e:
                print(f"❌ Error checking database {db_path}: {e}")
        else:
            print(f"⏭️  Database not found: {db_path}")

    print(f"\n🎉 Migration completed successfully on {success_count} database(s)!")
    return 0 if success_count > 0 else 1

if __name__ == "__main__":
    sys.exit(main())
