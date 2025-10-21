#!/usr/bin/env python3
"""
Add Lyreco signature and auto-response pattern
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from src.database import init_database, SkipTextBlock

def add_lyreco_pattern():
    """Add Lyreco pattern to catch signatures and auto-responses"""
    SessionMaker = init_database()
    session = SessionMaker()

    # Pattern to match Lyreco signatures, auto-responses, and footers
    lyreco_pattern = r'(Ihre\s+Anfrage\s+ist\s+eingegangen.*?Ihr\s+Lyreco\s+Kundenservice|Für\s+weitere\s+Fragen\s+stehen\s+wir\s+Ihnen.*?Lyreco\s+Deutschland\s+GmbH.*?www\.lyreco\.de|Sie\s+haben\s+Fragen\?.*?HELPCENTER.*?WEBSHOP|Ticketnummer\s+zu\s+Ihrer\s+Anfrage\s+\d+|Diese\s+E-Mail\s+ist\s+ein\s+Service\s+von\s+Lyreco\.)'

    try:
        # Check if similar pattern already exists
        existing = session.query(SkipTextBlock).filter(
            SkipTextBlock.pattern.like('%Lyreco%')
        ).all()

        if existing:
            print(f"Found {len(existing)} existing Lyreco patterns:")
            for p in existing:
                print(f"  [{p.id}] Regex={p.is_regex} Enabled={p.enabled}")
                print(f"      {p.pattern[:100]}...")

            response = input("\nAdd new pattern anyway? (y/n): ")
            if response.lower() != 'y':
                print("Cancelled.")
                return False

        # Add the pattern
        pattern = SkipTextBlock(
            pattern=lyreco_pattern,
            description='Lyreco signatures, auto-responses, and footers',
            is_regex=True,
            enabled=True
        )
        session.add(pattern)
        session.commit()

        print(f"\n✅ Added Lyreco pattern (ID: {pattern.id})")
        print(f"   Pattern: {lyreco_pattern[:100]}...")
        print(f"\nThis will match:")
        print("  - 'Ihre Anfrage ist eingegangen' auto-responses")
        print("  - 'Für weitere Fragen...' footer with address")
        print("  - 'Sie haben Fragen? ... HELPCENTER ... WEBSHOP'")
        print("  - 'Ticketnummer zu Ihrer Anfrage'")
        print("  - 'Diese E-Mail ist ein Service von Lyreco'")

        return True

    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()


if __name__ == '__main__':
    success = add_lyreco_pattern()
    sys.exit(0 if success else 1)
