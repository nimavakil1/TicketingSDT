#!/usr/bin/env python3
"""
Initialize database without starting the server
This creates the database with the old schema so migration can run
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from database.models import init_database

if __name__ == "__main__":
    print("Initializing database...")
    session_maker = init_database()
    print("✓ Database initialized successfully")
    print("Now run: python3 migrate_message_system.py")
