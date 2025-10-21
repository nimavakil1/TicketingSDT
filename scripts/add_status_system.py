#!/usr/bin/env python3
"""
Add custom status system for tickets
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from src.database import init_database
from sqlalchemy import text

def add_status_system():
    """Add custom status table and default statuses"""
    SessionMaker = init_database()
    session = SessionMaker()

    try:
        # Create custom_statuses table
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS custom_statuses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(50) NOT NULL UNIQUE,
                color VARCHAR(20) DEFAULT 'gray',
                is_closed BOOLEAN DEFAULT 0,
                display_order INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Add custom_status_id column to ticket_states
        try:
            session.execute(text("ALTER TABLE ticket_states ADD COLUMN custom_status_id INTEGER"))
            print("✅ Added custom_status_id column to ticket_states")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                print("⚠️  custom_status_id column already exists")
            else:
                raise

        # Add default statuses
        default_statuses = [
            ('New', 'blue', 0, 1),
            ('In Progress', 'yellow', 0, 2),
            ('Waiting for Customer', 'orange', 0, 3),
            ('Waiting for Supplier', 'purple', 0, 4),
            ('Resolved', 'green', 0, 5),
            ('Closed', 'gray', 1, 6),
        ]

        for name, color, is_closed, order in default_statuses:
            existing = session.execute(text("SELECT id FROM custom_statuses WHERE name = :name"), {'name': name}).fetchone()
            if not existing:
                session.execute(text("""
                    INSERT INTO custom_statuses (name, color, is_closed, display_order)
                    VALUES (:name, :color, :is_closed, :order)
                """), {'name': name, 'color': color, 'is_closed': is_closed, 'order': order})
                print(f"✅ Added status: {name}")
            else:
                print(f"⚠️  Status already exists: {name}")

        session.commit()

        print(f"\n{'='*60}")
        print("✅ Status system created successfully!")
        print(f"{'='*60}")
        print("\nDefault statuses:")
        statuses = session.execute(text("SELECT name, color, is_closed FROM custom_statuses ORDER BY display_order")).fetchall()
        for name, color, is_closed in statuses:
            closed_marker = " (CLOSED)" if is_closed else ""
            print(f"  • {name} [{color}]{closed_marker}")

        return True

    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()


if __name__ == '__main__':
    success = add_status_system()
    sys.exit(0 if success else 1)
