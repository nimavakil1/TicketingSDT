#!/usr/bin/env python3
"""
Complete Database Schema Fix
Checks and adds ALL missing columns from the models
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text, inspect
from config.settings import settings
import structlog

logger = structlog.get_logger(__name__)


def check_and_add_column(conn, table_name, column_name, column_def, default_value=None):
    """Check if column exists and add if missing"""
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns(table_name)]

    if column_name not in columns:
        print(f"  Adding '{column_name}' column...")
        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"))
        if default_value:
            conn.execute(text(f"UPDATE {table_name} SET {column_name} = {default_value} WHERE {column_name} IS NULL"))
        conn.commit()
        print(f"  ✓ Added '{column_name}' column")
        return True
    else:
        print(f"  ✓ '{column_name}' column exists")
        return False


def migrate_database():
    """Add all missing columns to database"""

    engine = create_engine(settings.database_url)

    print("=" * 60)
    print("COMPREHENSIVE DATABASE MIGRATION")
    print("=" * 60)

    with engine.connect() as conn:
        # 1. processed_emails table
        print("\n📧 Checking processed_emails table...")
        check_and_add_column(conn, 'processed_emails', 'success', 'BOOLEAN', '1')
        check_and_add_column(conn, 'processed_emails', 'error_message', 'TEXT')

        # 2. ai_decision_logs table - ALL columns
        print("\n🤖 Checking ai_decision_logs table...")

        # Check what columns currently exist
        inspector = inspect(conn)
        existing_cols = [col['name'] for col in inspector.get_columns('ai_decision_logs')]
        print(f"  Current columns: {', '.join(existing_cols)}")

        # Add missing columns
        check_and_add_column(conn, 'ai_decision_logs', 'feedback', 'VARCHAR(20)')
        check_and_add_column(conn, 'ai_decision_logs', 'feedback_notes', 'TEXT')
        check_and_add_column(conn, 'ai_decision_logs', 'timestamp', 'DATETIME')

        # If timestamp was added, copy from created_at if it exists
        if 'timestamp' not in existing_cols and 'created_at' in existing_cols:
            print("  Copying created_at to timestamp for existing records...")
            conn.execute(text("UPDATE ai_decision_logs SET timestamp = created_at WHERE timestamp IS NULL"))
            conn.commit()
            print("  ✓ Populated timestamp from created_at")

        # 3. ticket_states table - check for any schema issues
        print("\n🎫 Checking ticket_states table...")
        ticket_cols = [col['name'] for col in inspector.get_columns('ticket_states')]

        required_cols = ['current_state', 'updated_at', 'last_action_date']
        missing = [col for col in required_cols if col not in ticket_cols]
        if missing:
            print(f"  ⚠️  Missing columns: {', '.join(missing)}")
        else:
            print(f"  ✓ All required columns exist")

        # Verify everything works
        print("\n🔍 Verifying schema...")
        try:
            result = conn.execute(text("SELECT COUNT(*) FROM ai_decision_logs WHERE timestamp IS NOT NULL"))
            count = result.scalar()
            print(f"  ✓ ai_decision_logs accessible with timestamp ({count} records with timestamp)")
        except Exception as e:
            print(f"  ❌ Error: {e}")

        try:
            result = conn.execute(text("SELECT COUNT(*) FROM processed_emails WHERE success IS NOT NULL"))
            count = result.scalar()
            print(f"  ✓ processed_emails accessible with success ({count} records)")
        except Exception as e:
            print(f"  ❌ Error: {e}")

        print("\n" + "=" * 60)
        print("✅ Migration completed!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Restart API: sudo systemctl restart ai-agent-api")
        print("  2. Test API: curl -H 'Authorization: Bearer TOKEN' http://localhost:8002/api/dashboard/stats")
        print("  3. Check UI: https://ai.distri-smart.com")
        print("=" * 60)


if __name__ == "__main__":
    logger.info("Starting comprehensive database migration")
    logger.info("Database URL", url=settings.database_url)

    try:
        migrate_database()
        sys.exit(0)
    except Exception as e:
        logger.error("Migration failed", error=str(e), exc_info=True)
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
