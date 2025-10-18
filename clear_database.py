#!/usr/bin/env python3
"""
Script to clear all tickets and AI decisions from the database
"""
import sqlite3
from pathlib import Path

def clear_database(db_path: str):
    """Clear all tickets and AI decisions"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tables = [
        'ai_decision_logs',
        'pending_messages',
        'supplier_messages',
        'processed_emails',
        'ticket_states',
        'pending_email_retries'
    ]

    try:
        for table in tables:
            cursor.execute(f"DELETE FROM {table}")
            conn.commit()
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"✓ Cleared {table}: {count} rows remaining")

        print("\n✓ Database cleared successfully!")

    except Exception as e:
        print(f"Error clearing database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    db_path = "data/support_agent.db"

    if not Path(db_path).exists():
        print(f"Error: Database file '{db_path}' not found")
        exit(1)

    print("Clearing database...")
    clear_database(db_path)
