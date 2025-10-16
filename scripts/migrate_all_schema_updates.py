#!/usr/bin/env python3
"""
Complete Database Migration Script
Adds all missing columns to bring schema up to date
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


def check_column_exists(inspector, table_name, column_name):
    """Check if a column exists in a table"""
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def migrate_database():
    """Add all missing columns to database"""

    engine = create_engine(settings.database_url)
    inspector = inspect(engine)

    print("=" * 60)
    print("DATABASE MIGRATION - Schema Updates")
    print("=" * 60)

    with engine.connect() as conn:
        # 1. Migrate processed_emails table
        print("\n📧 Checking processed_emails table...")

        if not check_column_exists(inspector, 'processed_emails', 'success'):
            print("  Adding 'success' column...")
            conn.execute(text("ALTER TABLE processed_emails ADD COLUMN success BOOLEAN"))
            conn.execute(text("UPDATE processed_emails SET success = 1 WHERE success IS NULL"))
            conn.commit()
            print("  ✓ Added 'success' column")
        else:
            print("  ✓ 'success' column already exists")

        if not check_column_exists(inspector, 'processed_emails', 'error_message'):
            print("  Adding 'error_message' column...")
            conn.execute(text("ALTER TABLE processed_emails ADD COLUMN error_message TEXT"))
            conn.commit()
            print("  ✓ Added 'error_message' column")
        else:
            print("  ✓ 'error_message' column already exists")

        # 2. Migrate ai_decision_logs table
        print("\n🤖 Checking ai_decision_logs table...")

        if not check_column_exists(inspector, 'ai_decision_logs', 'feedback'):
            print("  Adding 'feedback' column...")
            conn.execute(text("ALTER TABLE ai_decision_logs ADD COLUMN feedback VARCHAR(20)"))
            conn.commit()
            print("  ✓ Added 'feedback' column")
        else:
            print("  ✓ 'feedback' column already exists")

        if not check_column_exists(inspector, 'ai_decision_logs', 'feedback_notes'):
            print("  Adding 'feedback_notes' column...")
            conn.execute(text("ALTER TABLE ai_decision_logs ADD COLUMN feedback_notes TEXT"))
            conn.commit()
            print("  ✓ Added 'feedback_notes' column")
        else:
            print("  ✓ 'feedback_notes' column already exists")

        # Verify the table now works
        print("\n🔍 Verifying schema...")
        try:
            result = conn.execute(text("SELECT COUNT(*) FROM ai_decision_logs"))
            count = result.scalar()
            print(f"  ✓ ai_decision_logs table accessible ({count} records)")
        except Exception as e:
            print(f"  ❌ Error accessing ai_decision_logs: {e}")

        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Restart API: sudo systemctl restart ai-agent-api")
        print("  2. Check UI at: https://ai.distri-smart.com")
        print("=" * 60)


if __name__ == "__main__":
    logger.info("Starting complete database migration")
    logger.info("Database URL", url=settings.database_url)

    try:
        migrate_database()
        sys.exit(0)
    except Exception as e:
        logger.error("Migration failed", error=str(e), exc_info=True)
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)
