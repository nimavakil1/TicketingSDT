#!/usr/bin/env python3
"""
Reset a user's password
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from config.settings import settings
from src.database.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def reset_password(username: str, new_password: str):
    """Reset user password"""

    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Find user
        user = session.query(User).filter(User.username == username).first()

        if not user:
            print(f"❌ User '{username}' not found")
            return False

        # Hash new password
        password_hash = pwd_context.hash(new_password)

        # Update password
        user.password_hash = password_hash
        session.commit()

        print(f"✅ Password reset successfully for user '{username}'")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        session.rollback()
        return False
    finally:
        session.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 reset_user_password.py <username> <new_password>")
        print("\nExample:")
        print("  python3 reset_user_password.py nima NewPassword123")
        sys.exit(1)

    username = sys.argv[1]
    new_password = sys.argv[2]

    if len(new_password) < 8:
        print("❌ Password must be at least 8 characters long")
        sys.exit(1)

    reset_password(username, new_password)
