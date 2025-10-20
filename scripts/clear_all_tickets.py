#!/usr/bin/env python3
"""
Clear all tickets, decisions, and messages from database
Keeps users and configuration intact
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from src.database.db import SessionLocal
from sqlalchemy import text

def clear_all_tickets():
    """Clear all ticket-related data from database"""
    session = SessionLocal()

    try:
        print("🗑️  Clearing all tickets and related data...")

        # Order matters due to foreign key constraints
        tables_to_clear = [
            'pending_messages',
            'ai_decision_logs',
            'pending_email_retries',
            'processed_emails',
            'ticket_states'
        ]

        for table in tables_to_clear:
            result = session.execute(text(f"DELETE FROM {table}"))
            count = result.rowcount
            session.commit()
            print(f"  ✓ Cleared {count} records from {table}")

        print("\n✅ All tickets cleared successfully!")
        print("   - Users preserved")
        print("   - Settings preserved")
        print("   - Templates preserved")
        print("   - Text filters preserved")

        return True

    except Exception as e:
        session.rollback()
        print(f"\n❌ Error: {e}")
        return False
    finally:
        session.close()

if __name__ == '__main__':
    print("⚠️  WARNING: This will delete ALL tickets and AI decisions!")
    print("   Users and settings will be preserved.\n")

    response = input("Are you sure you want to continue? (yes/no): ")

    if response.lower() == 'yes':
        success = clear_all_tickets()
        sys.exit(0 if success else 1)
    else:
        print("❌ Cancelled")
        sys.exit(1)
