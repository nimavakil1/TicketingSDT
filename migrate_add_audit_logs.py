#!/usr/bin/env python3
"""
Migration script to add ticket_audit_logs table
Run this once to update the database schema
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from src.database.models import init_database, Base, TicketAuditLog
from sqlalchemy import inspect

print("Initializing database connection...")
SessionLocal = init_database()
db = SessionLocal()

try:
    # Check if table already exists
    inspector = inspect(db.bind)
    existing_tables = inspector.get_table_names()

    print(f"\nExisting tables: {', '.join(existing_tables)}")

    if 'ticket_audit_logs' in existing_tables:
        print("\n✓ ticket_audit_logs table already exists - no migration needed")
    else:
        print("\n→ Creating ticket_audit_logs table...")
        # Create only the new table
        TicketAuditLog.__table__.create(db.bind, checkfirst=True)
        print("✓ ticket_audit_logs table created successfully")

    print("\n✅ Migration completed successfully!")

except Exception as e:
    print(f"\n❌ Migration failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

finally:
    db.close()
