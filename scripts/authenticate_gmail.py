#!/usr/bin/env python3
"""
Authenticate Gmail API
Generates OAuth URL for remote authentication
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from config.settings import settings
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.labels',
    'https://www.googleapis.com/auth/gmail.send',
]

def authenticate():
    """Authenticate with Gmail API"""
    credentials_path = settings.gmail_credentials_path
    token_path = settings.gmail_token_path

    print("=" * 60)
    print("Gmail API Authentication")
    print("=" * 60)

    if not os.path.exists(credentials_path):
        print(f"\n❌ Credentials file not found at: {credentials_path}")
        print("\nYou need to download OAuth2 credentials from Google Cloud Console:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Select your project")
        print("3. Go to APIs & Services > Credentials")
        print("4. Download OAuth 2.0 Client ID credentials")
        print(f"5. Save as {credentials_path}")
        return False

    print(f"\n✓ Found credentials at: {credentials_path}")
    print(f"✓ Token will be saved to: {token_path}")

    # Ensure token directory exists
    token_dir = os.path.dirname(token_path)
    if token_dir and not os.path.exists(token_dir):
        os.makedirs(token_dir, exist_ok=True)
        print(f"✓ Created directory: {token_dir}")

    print("\n📋 Requesting these permissions:")
    for scope in SCOPES:
        print(f"  - {scope.split('/')[-1].upper()}")

    print("\n🔐 Starting OAuth flow...")
    print("=" * 60)

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            credentials_path,
            SCOPES,
            redirect_uri='urn:ietf:wg:oauth:2.0:oob'  # For manual code entry
        )

        # This will print the URL and wait for manual code entry
        creds = flow.run_console()

        # Save credentials
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

        print("\n" + "=" * 60)
        print("✅ Authentication successful!")
        print(f"✅ Token saved to: {token_path}")
        print("=" * 60)

        # Verify scopes
        print("\n📋 Granted scopes:")
        if hasattr(creds, 'scopes'):
            for scope in creds.scopes:
                print(f"  ✓ {scope}")

        return True

    except Exception as e:
        print(f"\n❌ Authentication failed: {e}")
        return False

if __name__ == '__main__':
    success = authenticate()
    sys.exit(0 if success else 1)
