#!/usr/bin/env python3
"""
Add patterns to remove ticket system metadata and job titles
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from src.database import init_database, SkipTextBlock

def add_metadata_patterns():
    """Add patterns to remove ticket metadata and signatures"""
    SessionMaker = init_database()
    session = SessionMaker()

    patterns = [
        {
            'pattern': r'Aktualisiert\s+von:\s+[^,]+,\s+\d{1,2}\.\s+\w+\.\s+\d{4},\s+\d{2}:\d{2}\s+\w+',
            'description': 'Ticket update timestamps (Aktualisiert von: Name, Date)',
            'is_regex': True
        },
        {
            'pattern': r'(Customer\s+Care\s+Agent|Special\s+Customers|Kundenservice|Support\s+Team)\s*$',
            'description': 'Job titles and department names at end of line',
            'is_regex': True
        },
        {
            'pattern': r'Anhänge?:\s+[^\n]+\.(jpg|jpeg|png|pdf|doc|docx)\s+-\s+https?://[^\s]+',
            'description': 'Attachment references with URLs',
            'is_regex': True
        },
        {
            'pattern': r'\[[A-Z0-9]{6,}-[A-Z0-9]{5,}\]',
            'description': 'Reference codes in brackets like [96V6DD-EGVYR]',
            'is_regex': True
        },
        {
            'pattern': r'[\u200B-\u200D\uFEFF]+',
            'description': 'Zero-width spaces and invisible characters',
            'is_regex': True
        },
        {
            'pattern': r'Ihr\s+(Distri-Smart|PaperSmart)\s+Team\s*',
            'description': 'Our own team signature (to avoid quoting ourselves)',
            'is_regex': True
        }
    ]

    try:
        added = 0
        for pat in patterns:
            # Check if similar pattern exists
            existing = session.query(SkipTextBlock).filter(
                SkipTextBlock.pattern == pat['pattern']
            ).first()

            if existing:
                print(f"⚠️  Pattern already exists: {pat['description']}")
                continue

            pattern = SkipTextBlock(
                pattern=pat['pattern'],
                description=pat['description'],
                is_regex=pat['is_regex'],
                enabled=True
            )
            session.add(pattern)
            added += 1
            print(f"✅ Added: {pat['description']}")
            print(f"   Pattern: {pat['pattern'][:80]}...")

        session.commit()

        print(f"\n{'='*60}")
        print(f"✅ Added {added} new patterns")
        print(f"{'='*60}")

        print("\nThese patterns will remove:")
        print("  - 'Aktualisiert von: Name, Date' timestamp headers")
        print("  - Job titles like 'Customer Care Agent', 'Special Customers'")
        print("  - 'Anhänge: filename.jpg - https://...' attachment links")
        print("  - Reference codes like '[96V6DD-EGVYR]'")
        print("  - Zero-width invisible characters")
        print("  - Our own 'Ihr Distri-Smart Team' signatures")

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
    success = add_metadata_patterns()
    sys.exit(0 if success else 1)
