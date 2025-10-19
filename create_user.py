#!/usr/bin/env python3
"""
Script to create or update a user in the database
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from passlib.context import CryptContext
from src.database.connection import SessionLocal
from src.database.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_or_update_user(username: str, password: str, role: str = "admin"):
    """Create or update a user"""
    db = SessionLocal()

    try:
        # Check if user exists
        user = db.query(User).filter(User.username == username).first()

        if user:
            print(f"User '{username}' already exists. Updating password...")
            user.password_hash = pwd_context.hash(password)
            user.role = role
        else:
            print(f"Creating new user '{username}'...")
            password_hash = pwd_context.hash(password)
            user = User(
                username=username,
                password_hash=password_hash,
                role=role
            )
            db.add(user)

        db.commit()
        print(f"✓ User '{username}' ready with role '{role}'")

        # Show all users
        all_users = db.query(User).all()
        print(f"\nTotal users in database: {len(all_users)}")
        for u in all_users:
            print(f"  - {u.username} (role: {u.role})")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 create_user.py <username> <password> [role]")
        print("Example: python3 create_user.py nima Sage2o15 admin")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    role = sys.argv[3] if len(sys.argv) > 3 else "admin"

    create_or_update_user(username, password, role)
