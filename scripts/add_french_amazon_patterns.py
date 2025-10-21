#!/usr/bin/env python3
"""
Add French Amazon message patterns
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from src.database import init_database, SkipTextBlock

def add_french_patterns():
    """Add French Amazon patterns"""
    SessionMaker = init_database()
    session = SessionMaker()

    patterns = [
        {
            'pattern': r'Vous avez re[cç]u un message\.',
            'description': 'French Amazon notification header',
            'is_regex': True
        },
        {
            'pattern': r'#\s+[\d\-]+:\s+\d+\s+/\s+[^\[]+\[ASIN:\s+[A-Z0-9]+\]',
            'description': 'Amazon order header with ASIN (all languages)',
            'is_regex': True
        },
        {
            'pattern': r'-{10,}\s+(Message|Fin du message)\s*:?\s*-{10,}',
            'description': 'Message separator lines (French/multilingual)',
            'is_regex': True
        },
        {
            'pattern': r'Cet e-mail a-t-il été utile\s*\?\s+https://sellercentral\.amazon\.[a-z]+/gp/satisfaction/[^\s]+',
            'description': 'French Amazon survey link',
            'is_regex': True
        },
        {
            'pattern': r'Résoudre le cas\s+https://sellercentral\.amazon\.[a-z]+/messaging/no-response-needed[^\s]*',
            'description': 'French Amazon resolve case link',
            'is_regex': True
        },
        {
            'pattern': r'Signaler une activité suspecte\s+https://sellercentral\.amazon\.[a-z]+/messaging/report[^\s]*',
            'description': 'French Amazon report suspicious activity link',
            'is_regex': True
        },
        {
            'pattern': r'Droits d\'auteur\s+\d{4}\s+Amazon,?\s+Inc\.\s+ou\s+ses\s+filiales\.\s+Tous\s+droits\s+réservés\..*?Numéro\s+d\'identification\s+à\s+TVA\s+luxembourgeoise\s*:\s*LU\s+\d+',
            'description': 'French Amazon copyright footer',
            'is_regex': True
        },
        {
            'pattern': r'Important\s*:\s*Lorsque\s+vous\s+répondez\s+à\s+ce\s+message.*?En\s+utilisant\s+ce\s+service,\s+vous\s+acceptez\s+ces\s+conditions\.',
            'description': 'French Amazon legal disclaimer',
            'is_regex': True
        },
        {
            'pattern': r'Nous\s+espérons\s+que\s+ce\s+message\s+vous\s+a\s+été\s+utile\..*?veuillez\s+vous\s+désinscrire\.',
            'description': 'French Amazon unsubscribe footer',
            'is_regex': True
        },
        {
            'pattern': r'Faites\s+vos\s+achats\s+sur\s+Amazon\.[a-z]+\s+en\s+toute\s+confiance\..*?garantie\s+d\'achat\s+sécurisé\.',
            'description': 'French Amazon purchase confidence notice',
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
        print(f"✅ Added {added} new French Amazon patterns")
        print(f"{'='*60}")

        print("\nThese patterns will remove:")
        print("  - 'Vous avez reçu un message' headers")
        print("  - Order lines with ASIN codes")
        print("  - Message separator lines (----------)")
        print("  - French Amazon survey/action links")
        print("  - French Amazon copyright footer")
        print("  - French Amazon legal disclaimer")
        print("  - French Amazon unsubscribe notices")

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
    success = add_french_patterns()
    sys.exit(0 if success else 1)
