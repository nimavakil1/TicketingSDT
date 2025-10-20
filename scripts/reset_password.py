#!/usr/bin/env python3
"""
Reset password for a user
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from src.database.db import SessionLocal
from src.database.models import User
import bcrypt

def reset_password(username: str, new_password: str):
    """Reset password for a user"""
    session = SessionLocal()

    try:
        user = session.query(User).filter(User.username == username).first()

        if not user:
            print(f"✗ User '{username}' not found")
            return False

        # Hash the new password
        hashed_password = bcrypt.hashpw(
            new_password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        # Update password
        user.hashed_password = hashed_password
        session.commit()

        print(f"✓ Password reset successfully for user '{username}'")
        return True

    except Exception as e:
        session.rollback()
        print(f"✗ Error: {e}")
        return False
    finally:
        session.close()

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python3 reset_password.py <username> <new_password>")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]

    success = reset_password(username, password)
    sys.exit(0 if success else 1)
