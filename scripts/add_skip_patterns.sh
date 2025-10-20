#!/bin/bash
# Wrapper script to add skip patterns with correct Python path

cd ~/TicketingSDT

python3 << 'PYTHON_SCRIPT'
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

# Set up paths
sys.path.insert(0, os.getcwd())
os.chdir(os.getcwd())

from src.database import init_database, SkipTextBlock

# Initialize database
SessionMaker = init_database()
SessionLocal = SessionMaker

def add_boilerplate_patterns():
    """Add common boilerplate patterns to database"""
    session = SessionLocal()

    patterns = [
        # Amazon footers
        {
            'pattern': 'War diese E-Mail hilfreich?',
            'description': 'Amazon survey link',
            'is_regex': False,
            'enabled': True
        },
        {
            'pattern': 'Copyright 2025 Amazon Inc.',
            'description': 'Amazon copyright footer',
            'is_regex': False,
            'enabled': True
        },
        {
            'pattern': 'Copyright © 2025 Amazon Inc.',
            'description': 'Amazon copyright footer variant',
            'is_regex': False,
            'enabled': True
        },
        {
            'pattern': 'Wir speichern den Nachrichtenverkehr',
            'description': 'Amazon privacy notice',
            'is_regex': False,
            'enabled': True
        },

        # Supplier signatures
        {
            'pattern': 'Diese E-Mail ist ein Service von',
            'description': 'Supplier email service notice',
            'is_regex': False,
            'enabled': True
        },
        {
            'pattern': 'Elektronische Kommunikation kann Viren enthalten',
            'description': 'Email disclaimer',
            'is_regex': False,
            'enabled': True
        },
        {
            'pattern': 'Diese Nachricht wurde automatisch generiert',
            'description': 'Auto-generated message notice',
            'is_regex': False,
            'enabled': True
        },

        # HTML signatures and separators (regex patterns)
        {
            'pattern': r'<table[^>]*>.*?</table>',
            'description': 'HTML email signature tables',
            'is_regex': True,
            'enabled': True
        },
        {
            'pattern': r'[-_]{20,}',
            'description': 'Long separator lines (dashes/underscores)',
            'is_regex': True,
            'enabled': True
        },
        {
            'pattern': r'={20,}',
            'description': 'Equals separator lines',
            'is_regex': True,
            'enabled': True
        },
    ]

    try:
        added = 0
        skipped = 0

        for pattern_data in patterns:
            # Check if pattern already exists
            existing = session.query(SkipTextBlock).filter_by(
                pattern=pattern_data['pattern']
            ).first()

            if existing:
                print(f"⚠️  Skipping (already exists): {pattern_data['description']}")
                skipped += 1
                continue

            # Add new pattern
            skip_block = SkipTextBlock(**pattern_data)
            session.add(skip_block)
            print(f"✅ Added: {pattern_data['description']}")
            added += 1

        session.commit()

        print(f"\n{'='*60}")
        print(f"✅ Added {added} new patterns")
        if skipped > 0:
            print(f"⚠️  Skipped {skipped} existing patterns")
        print(f"{'='*60}\n")

        return True

    except Exception as e:
        session.rollback()
        print(f"\n❌ Error adding patterns: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()

# Main
add_boilerplate_patterns()

PYTHON_SCRIPT
