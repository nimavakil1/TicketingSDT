#!/usr/bin/env python3
"""
Migration script to add system_settings table
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Change to project directory
os.chdir(project_root)

from src.database.db import SessionLocal, engine
from sqlalchemy import text

def migrate():
    """Add system_settings table"""
    session = SessionLocal()

    try:
        # Create system_settings table
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Insert default value for gmail_monitoring_paused
        session.execute(text("""
            INSERT OR REPLACE INTO system_settings (key, value)
            VALUES ('gmail_monitoring_paused', 'false')
        """))

        session.commit()
        print("✓ System settings table created successfully")
        print("✓ Gmail monitoring is ACTIVE (not paused)")

    except Exception as e:
        session.rollback()
        print(f"✗ Error: {e}")
        return False
    finally:
        session.close()

    return True

if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)
