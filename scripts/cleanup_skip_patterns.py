#!/usr/bin/env python3
"""
Clean up redundant skip text blocks
Keep regex patterns, remove overlapping plain text patterns
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from src.database import init_database, SkipTextBlock

def cleanup_skip_patterns():
    """Remove redundant skip patterns"""
    SessionMaker = init_database()
    session = SessionMaker()

    try:
        # Get all patterns
        all_patterns = session.query(SkipTextBlock).all()

        # Separate regex and plain text
        regex_patterns = [p for p in all_patterns if p.is_regex]
        text_patterns = [p for p in all_patterns if not p.is_regex]

        print(f"Found {len(regex_patterns)} regex patterns and {len(text_patterns)} text patterns")
        print("\n" + "="*60)

        # Define IDs to delete (redundant plain text patterns)
        # These are covered by the regex patterns or are just greetings
        ids_to_delete = [
            1,   # "Du hast eine Nachricht erhalten." - not important
            2,   # Amazon buttons - covered by regex
            3,   # Amazon footer - covered by regex 22, 39, 40
            4,   # Lyreco signature - covered by regex
            5,   # Lyreco help text - covered by regex
            6,   # "Mit freundlichen Grüßen" - greeting, covered by regex 13
            7,   # Distri-Smart signature - our own, keep? Actually delete, we control this
            8,   # Amazon returns text - very long, covered by regex 44
            9,   # PBS signature - covered by separator regex
            10,  # French Amazon footer - very long, covered by regex
            11,  # "Freundliche Grüße" - covered by regex 13
            12,  # "Best regards" - covered by regex 13
            14,  # "Amazon Business..." - covered by regex
            15,  # "Liebe(r) Amazon-Seller..." - not important intro
            16,  # "Bitte antworten Sie..." - covered by regex
            17,  # Long Amazon returns text - covered by regex 44
            18,  # Amazon footer variant - covered by regex 39, 40
            24,  # HTML table start - covered by regex 34
            25,  # Lyreco signature with HTML - covered by regex
            26,  # "Diese E-Mail ist ein Service von Lyreco" - covered by regex 31
            27,  # "War diese E-Mail hilfreich?" - covered by regex 19
            28,  # "Copyright 2025 Amazon Inc." - covered by regex 40
            29,  # "Copyright © 2025 Amazon Inc." - covered by regex 40
            30,  # "Wir speichern den Nachrichtenverkehr" - covered by regex 41
            31,  # "Diese E-Mail ist ein Service von" - generic, keep as text
            32,  # "Elektronische Kommunikation..." - not important
            33,  # "Diese Nachricht wurde automatisch generiert" - not important
            37,  # Amazon footer variant - covered by regex 39
            38,  # Lyreco help text variant - covered by regex
        ]

        print("Patterns to DELETE (redundant):")
        print("-" * 60)
        deleted = 0
        for pattern_id in ids_to_delete:
            pattern = session.query(SkipTextBlock).filter_by(id=pattern_id).first()
            if pattern:
                desc = pattern.description or "No description"
                preview = pattern.pattern[:60] + "..." if len(pattern.pattern) > 60 else pattern.pattern
                print(f"  [{pattern_id}] {desc}")
                print(f"       {preview}")
                session.delete(pattern)
                deleted += 1

        print(f"\n{'='*60}")
        print(f"Deleting {deleted} redundant patterns...")
        session.commit()

        # Show remaining patterns
        remaining = session.query(SkipTextBlock).order_by(
            SkipTextBlock.is_regex.desc(),
            SkipTextBlock.id
        ).all()

        print(f"\n{'='*60}")
        print(f"REMAINING PATTERNS ({len(remaining)}):")
        print("="*60)

        print("\nREGEX PATTERNS:")
        for p in remaining:
            if p.is_regex:
                preview = p.pattern[:80] + "..." if len(p.pattern) > 80 else p.pattern
                desc = p.description or "No description"
                print(f"  [{p.id}] {desc}")
                print(f"       Pattern: {preview}")

        print("\nPLAIN TEXT PATTERNS:")
        for p in remaining:
            if not p.is_regex:
                preview = p.pattern[:80] + "..." if len(p.pattern) > 80 else p.pattern
                desc = p.description or "No description"
                print(f"  [{p.id}] {desc}")
                print(f"       Text: {preview}")

        print(f"\n{'='*60}")
        print(f"✅ Cleanup complete!")
        print(f"   Deleted: {deleted} patterns")
        print(f"   Remaining: {len(remaining)} patterns")
        print(f"   - Regex: {sum(1 for p in remaining if p.is_regex)}")
        print(f"   - Text: {sum(1 for p in remaining if not p.is_regex)}")
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
    success = cleanup_skip_patterns()
    sys.exit(0 if success else 1)
