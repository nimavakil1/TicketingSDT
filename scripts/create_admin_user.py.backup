#!/usr/bin/env python3
"""
Create initial admin user for web UI
Run this script once to create your first admin account
"""
import sys
import os
from getpass import getpass

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from passlib.context import CryptContext
from src.database.db_manager import DatabaseManager
from src.database.models import User, Base

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_admin_user():
    """Create initial admin user"""
    print("=" * 60)
    print("Create Admin User for AI Agent Web UI")
    print("=" * 60)
    print()

    # Get user input
    username = input("Username: ").strip()
    if not username:
        print("Error: Username cannot be empty")
        return False

    email = input("Email: ").strip()
    if not email:
        print("Error: Email cannot be empty")
        return False

    password = getpass("Password: ")
    if not password:
        print("Error: Password cannot be empty")
        return False

    password_confirm = getpass("Confirm Password: ")
    if password != password_confirm:
        print("Error: Passwords do not match")
        return False

    # Initialize database
    print("\nInitializing database...")
    db_manager = DatabaseManager()

    # Create tables if they don't exist
    from sqlalchemy import create_engine
    from config.settings import settings
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)

    session = db_manager.get_session()

    try:
        # Check if user already exists
        existing_user = session.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing_user:
            print(f"\nError: User with username '{username}' or email '{email}' already exists")
            return False

        # Create new admin user
        password_hash = pwd_context.hash(password)
        new_user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            role='admin',
            full_name='Administrator',
            is_active=True
        )

        session.add(new_user)
        session.commit()

        print(f"\n✅ Admin user '{username}' created successfully!")
        print(f"   Email: {email}")
        print(f"   Role: admin")
        print("\nYou can now login to the web UI with these credentials.")
        return True

    except Exception as e:
        session.rollback()
        print(f"\n❌ Error creating user: {e}")
        return False

    finally:
        session.close()


if __name__ == "__main__":
    try:
        success = create_admin_user()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
        sys.exit(1)
