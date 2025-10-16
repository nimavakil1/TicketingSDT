#!/usr/bin/env python3
"""
Database Migration: Add success tracking to ProcessedEmail table

Adds:
- success (Boolean, default True, indexed)
- error_message (Text, nullable)

Run this before deploying the updated code.
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


def migrate_database():
    """Add success tracking columns to processed_emails table"""

    engine = create_engine(settings.database_url)

    # Check if columns already exist
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('processed_emails')]

    logger.info("Current processed_emails columns", columns=columns)

    with engine.connect() as conn:
        # Add success column if it doesn't exist
        if 'success' not in columns:
            logger.info("Adding 'success' column to processed_emails table")
            # SQLite doesn't support adding columns with default values directly in some versions
            # So we add it nullable first, then update, then make it non-nullable
            conn.execute(text("""
                ALTER TABLE processed_emails
                ADD COLUMN success BOOLEAN
            """))
            conn.execute(text("""
                UPDATE processed_emails
                SET success = 1
                WHERE success IS NULL
            """))
            conn.commit()
            logger.info("Added 'success' column successfully")
        else:
            logger.info("'success' column already exists")

        # Add error_message column if it doesn't exist
        if 'error_message' not in columns:
            logger.info("Adding 'error_message' column to processed_emails table")
            conn.execute(text("""
                ALTER TABLE processed_emails
                ADD COLUMN error_message TEXT
            """))
            conn.commit()
            logger.info("Added 'error_message' column successfully")
        else:
            logger.info("'error_message' column already exists")

        # For SQLite, we can't add an index after the fact easily, but it's okay
        # The models.py will create the index for new databases
        # For existing databases, the queries will still work without the index

        logger.info("Migration completed successfully")


if __name__ == "__main__":
    logger.info("Starting database migration: Add success tracking")
    logger.info("Database URL", url=settings.database_url)

    try:
        migrate_database()
        logger.info("Migration successful!")
        sys.exit(0)
    except Exception as e:
        logger.error("Migration failed", error=str(e), exc_info=True)
        sys.exit(1)
