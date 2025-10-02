#!/usr/bin/env python3
"""
Setup Verification Script
Checks that all components are properly configured
"""
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

def print_status(check, status, message=""):
    """Print status with colored output"""
    if status:
        print(f"✅ {check}")
        if message:
            print(f"   {message}")
    else:
        print(f"❌ {check}")
        if message:
            print(f"   {message}")
    return status

def verify_environment():
    """Verify Python environment"""
    print("\n🔍 Checking Python Environment...")

    # Python version
    version = sys.version_info
    status = version.major == 3 and version.minor >= 11
    print_status(
        "Python 3.11+",
        status,
        f"Found: Python {version.major}.{version.minor}.{version.micro}"
    )

    return status

def verify_dependencies():
    """Verify required packages"""
    print("\n🔍 Checking Dependencies...")

    packages = {
        'requests': 'HTTP client',
        'google': 'Google API',
        'sqlalchemy': 'Database',
        'pydantic': 'Configuration',
        'structlog': 'Logging',
        'langdetect': 'Language detection',
    }

    all_ok = True
    for package, description in packages.items():
        try:
            __import__(package)
            print_status(f"{package} ({description})", True)
        except ImportError:
            print_status(f"{package} ({description})", False, "Run: pip install -r requirements.txt")
            all_ok = False

    return all_ok

def verify_configuration():
    """Verify configuration files"""
    print("\n🔍 Checking Configuration...")

    checks = []

    # .env file
    env_exists = Path('.env').exists()
    checks.append(print_status(
        ".env file exists",
        env_exists,
        "Run: cp .env.example .env" if not env_exists else None
    ))

    if env_exists:
        # Load settings
        try:
            from config.settings import settings

            # Check AI provider
            ai_ok = bool(settings.ai_provider in ['openai', 'anthropic', 'gemini'])
            checks.append(print_status(
                f"AI provider configured ({settings.ai_provider})",
                ai_ok
            ))

            # Check AI key
            if settings.ai_provider == 'openai':
                key_ok = bool(settings.openai_api_key and len(settings.openai_api_key) > 10)
            elif settings.ai_provider == 'anthropic':
                key_ok = bool(settings.anthropic_api_key and len(settings.anthropic_api_key) > 10)
            else:
                key_ok = bool(settings.google_api_key and len(settings.google_api_key) > 10)

            checks.append(print_status(
                "AI API key set",
                key_ok,
                "Add API key to .env" if not key_ok else None
            ))

            # Check ticketing credentials
            ticket_ok = bool(settings.ticketing_api_username and settings.ticketing_api_password)
            checks.append(print_status(
                "Ticketing API credentials set",
                ticket_ok
            ))

            # Check Gmail config
            gmail_ok = bool(settings.gmail_support_email)
            checks.append(print_status(
                "Gmail support email configured",
                gmail_ok,
                "Set GMAIL_SUPPORT_EMAIL in .env" if not gmail_ok else None
            ))

        except Exception as e:
            checks.append(print_status(
                "Configuration loading",
                False,
                f"Error: {str(e)}"
            ))

    return all(checks)

def verify_gmail_credentials():
    """Verify Gmail OAuth credentials"""
    print("\n🔍 Checking Gmail Credentials...")

    creds_file = Path('config/gmail_credentials.json')
    token_file = Path('config/gmail_token.json')

    creds_ok = creds_file.exists()
    print_status(
        "Gmail OAuth credentials (gmail_credentials.json)",
        creds_ok,
        "Download from Google Cloud Console" if not creds_ok else "Found"
    )

    token_ok = token_file.exists()
    print_status(
        "Gmail token (gmail_token.json)",
        token_ok,
        "Run application first time to authenticate" if not token_ok else "Found"
    )

    return creds_ok

def verify_directories():
    """Verify required directories"""
    print("\n🔍 Checking Directories...")

    directories = ['data', 'logs', 'config']
    all_ok = True

    for dir_name in directories:
        dir_path = Path(dir_name)
        exists = dir_path.exists() and dir_path.is_dir()
        if not exists:
            dir_path.mkdir(exist_ok=True, parents=True)
            print_status(f"{dir_name}/ directory", True, "Created")
        else:
            print_status(f"{dir_name}/ directory", True, "Exists")

    return all_ok

def verify_database():
    """Verify database initialization"""
    print("\n🔍 Checking Database...")

    try:
        from src.database.models import init_database

        Session = init_database()
        session = Session()

        # Test query
        from src.database.models import Supplier
        suppliers = session.query(Supplier).count()

        session.close()

        print_status(
            "Database initialized",
            True,
            f"Found {suppliers} supplier(s)"
        )

        return True

    except Exception as e:
        print_status(
            "Database initialization",
            False,
            f"Error: {str(e)}"
        )
        return False

def verify_api_clients():
    """Verify API clients can be initialized"""
    print("\n🔍 Checking API Clients...")

    checks = []

    # Ticketing API
    try:
        from src.api.ticketing_client import TicketingAPIClient
        client = TicketingAPIClient()
        checks.append(print_status("Ticketing API client", True))
    except Exception as e:
        checks.append(print_status("Ticketing API client", False, str(e)))

    # AI Engine
    try:
        from src.ai.ai_engine import AIEngine
        engine = AIEngine()
        checks.append(print_status("AI Engine", True))
    except Exception as e:
        checks.append(print_status("AI Engine", False, str(e)))

    return all(checks)

def main():
    """Run all verification checks"""
    print("=" * 60)
    print("AI Support Agent - Setup Verification")
    print("=" * 60)

    results = []

    results.append(verify_environment())
    results.append(verify_dependencies())
    results.append(verify_directories())
    results.append(verify_configuration())
    results.append(verify_gmail_credentials())
    results.append(verify_database())
    results.append(verify_api_clients())

    # Summary
    print("\n" + "=" * 60)
    if all(results):
        print("✅ All Checks Passed!")
        print("=" * 60)
        print("\nYou're ready to run the agent:")
        print("  python main.py")
        return 0
    else:
        print("❌ Some Checks Failed")
        print("=" * 60)
        print("\nPlease fix the issues above before running the agent.")
        print("See GETTING_STARTED.md for help.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
