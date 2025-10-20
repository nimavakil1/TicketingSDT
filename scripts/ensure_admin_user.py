#!/usr/bin/env python3
"""
Ensure admin user exists in database
Creates default admin if no users exist
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.db import SessionLocal
from src.database.models import User
import bcrypt

def ensure_admin_exists():
    """Ensure at least one admin user exists"""
    session = SessionLocal()

    try:
        # Check if any users exist
        user_count = session.query(User).count()

        if user_count == 0:
            print("⚠️  No users found in database!")
            print("Creating default admin user...")

            # Create default admin
            default_username = "admin"
            default_password = "admin123"

            hashed_password = bcrypt.hashpw(
                default_password.encode('utf-8'),
                bcrypt.gensalt()
            ).decode('utf-8')

            admin_user = User(
                username=default_username,
                email="admin@distri-smart.com",
                hashed_password=hashed_password,
                role="admin",
                full_name="System Administrator"
            )

            session.add(admin_user)
            session.commit()

            print(f"✓ Created admin user: {default_username}")
            print(f"  Password: {default_password}")
            print("  ⚠️  CHANGE THIS PASSWORD IMMEDIATELY!")
            return True
        else:
            print(f"✓ Found {user_count} user(s) in database")
            # List all users
            users = session.query(User).all()
            for user in users:
                print(f"  - {user.username} (role: {user.role})")
            return False

    except Exception as e:
        session.rollback()
        print(f"✗ Error: {e}")
        return False
    finally:
        session.close()

if __name__ == '__main__':
    ensure_admin_exists()
