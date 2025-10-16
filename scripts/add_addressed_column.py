#!/usr/bin/env python3
"""
Add 'addressed' column to ai_decision_logs table
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


def add_addressed_column():
    """Add addressed column to ai_decision_logs"""

    engine = create_engine(settings.database_url)

    print("=" * 60)
    print("DATABASE MIGRATION - Add Addressed Column")
    print("=" * 60)

    with engine.connect() as conn:
        inspector = inspect(conn)
        columns = [col['name'] for col in inspector.get_columns('ai_decision_logs')]

        print("\n📊 Checking ai_decision_logs table...")

        if 'addressed' not in columns:
            print("  Adding 'addressed' column...")
            conn.execute(text(
                "ALTER TABLE ai_decision_logs ADD COLUMN addressed BOOLEAN DEFAULT 0"
            ))
            conn.commit()
            print("  ✓ Added 'addressed' column")
        else:
            print("  ✓ 'addressed' column already exists")

        print("\n" + "=" * 60)
        print("✅ Migration completed!")
        print("=" * 60)


if __name__ == "__main__":
    logger.info("Starting database migration")

    try:
        add_addressed_column()
        sys.exit(0)
    except Exception as e:
        logger.error("Migration failed", error=str(e), exc_info=True)
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
