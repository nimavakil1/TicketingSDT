#!/usr/bin/env python3
"""
Check Gmail OAuth scopes in existing token
"""
import json
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
os.chdir(project_root)

from config.settings import settings

def check_scopes():
    """Check what scopes are currently granted"""
    token_path = settings.gmail_token_path

    if not os.path.exists(token_path):
        print("❌ Token file not found at:", token_path)
        print("   You need to authenticate first")
        return

    try:
        with open(token_path, 'r') as f:
            token_data = json.load(f)

        scopes = token_data.get('scopes', [])

        print("\n📋 Current Gmail OAuth Scopes:")
        print("=" * 60)

        required_scopes = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.modify',
            'https://www.googleapis.com/auth/gmail.labels',
            'https://www.googleapis.com/auth/gmail.send',
        ]

        for scope in required_scopes:
            if scope in scopes:
                print(f"✅ {scope.split('/')[-1].upper()}: Granted")
            else:
                print(f"❌ {scope.split('/')[-1].upper()}: MISSING")

        print("=" * 60)

        missing_scopes = [s for s in required_scopes if s not in scopes]

        if missing_scopes:
            print("\n⚠️  MISSING SCOPES DETECTED!")
            print("You need to re-authenticate to grant these permissions:")
            for scope in missing_scopes:
                print(f"  - {scope}")
            print("\nTo re-authenticate, delete the token and restart the backend:")
            print(f"  rm {token_path}")
            print("  uvicorn src.api.web_api:app --host 0.0.0.0 --port 8000")
        else:
            print("\n✅ All required scopes are granted!")
            print("You can send emails via Gmail API.")

    except Exception as e:
        print(f"❌ Error reading token: {e}")

if __name__ == '__main__':
    check_scopes()
