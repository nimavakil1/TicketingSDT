#!/usr/bin/env python3
"""
Add prompt versioning support to database
- Create prompt_versions table
- Add prompt_version_id column to ai_decision_logs
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


def add_prompt_versioning():
    """Add prompt versioning tables and columns"""

    engine = create_engine(settings.database_url)

    print("=" * 60)
    print("DATABASE MIGRATION - Prompt Versioning")
    print("=" * 60)

    with engine.connect() as conn:
        inspector = inspect(conn)

        # Check if prompt_versions table exists
        tables = inspector.get_table_names()

        print("\n📋 Checking prompt_versions table...")
        if 'prompt_versions' not in tables:
            print("  Creating prompt_versions table...")
            conn.execute(text("""
                CREATE TABLE prompt_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version_number INTEGER NOT NULL UNIQUE,
                    prompt_text TEXT NOT NULL,
                    created_at DATETIME NOT NULL,
                    created_by VARCHAR(100),
                    change_summary TEXT,
                    feedback_count INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 0
                )
            """))
            conn.commit()
            print("  ✓ Created prompt_versions table")
        else:
            print("  ✓ prompt_versions table already exists")

        # Check if prompt_version_id column exists in ai_decision_logs
        print("\n📊 Checking ai_decision_logs table...")
        columns = [col['name'] for col in inspector.get_columns('ai_decision_logs')]

        if 'prompt_version_id' not in columns:
            print("  Adding 'prompt_version_id' column...")
            conn.execute(text(
                "ALTER TABLE ai_decision_logs ADD COLUMN prompt_version_id INTEGER"
            ))
            conn.commit()
            print("  ✓ Added 'prompt_version_id' column")
        else:
            print("  ✓ 'prompt_version_id' column already exists")

        print("\n" + "=" * 60)
        print("✅ Migration completed!")
        print("=" * 60)
        print("\nNote: prompt_version_id is nullable to support existing records.")
        print("New AI decisions will be linked to prompt versions automatically.")
        print("=" * 60)


if __name__ == "__main__":
    logger.info("Starting prompt versioning migration")

    try:
        add_prompt_versioning()
        sys.exit(0)
    except Exception as e:
        logger.error("Migration failed", error=str(e), exc_info=True)
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
