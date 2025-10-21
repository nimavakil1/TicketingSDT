#!/usr/bin/env python3
"""
Diagnose which skip pattern is filtering out a message
"""
import sys
import os
from pathlib import Path
import re

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from src.database import init_database, SkipTextBlock
from src.api.ticketing_client import TicketingAPIClient
from dotenv import load_dotenv

load_dotenv('.env')

def diagnose_message_filtering(ticket_number: str, message_date: str = None):
    """
    Test which skip patterns match a specific message
    """
    SessionMaker = init_database()
    session = SessionMaker()

    try:
        # Get ticket from API
        client = TicketingAPIClient()
        tickets = client.get_ticket_by_ticket_number(ticket_number)

        if not tickets:
            print(f"❌ Ticket {ticket_number} not found")
            return False

        ticket_data = tickets[0]
        ticket_details = ticket_data.get('ticketDetails', [])

        # Find the message by date if specified
        target_message = None
        if message_date:
            for detail in ticket_details:
                created = detail.get('createdDateTime', '')
                if message_date in created:
                    target_message = detail
                    break
        else:
            # Use the last message
            target_message = ticket_details[-1] if ticket_details else None

        if not target_message:
            print(f"❌ Message not found")
            print(f"Available messages:")
            for detail in ticket_details:
                print(f"  - {detail.get('createdDateTime')}: {detail.get('comment', '')[:60]}...")
            return False

        # Get message text
        message_text = target_message.get('comment', '') or target_message.get('entranceEmailBody', '')

        print(f"\n{'='*80}")
        print(f"TICKET: {ticket_number}")
        print(f"MESSAGE DATE: {target_message.get('createdDateTime')}")
        print(f"SOURCE: {target_message.get('sourceTicketSideTypeId')} -> TARGET: {target_message.get('targetTicketSideTypeId')}")
        print(f"{'='*80}")
        print(f"\nORIGINAL MESSAGE TEXT ({len(message_text)} chars):")
        print("-" * 80)
        print(message_text)
        print("-" * 80)

        # Get all skip patterns
        patterns = session.query(SkipTextBlock).filter_by(enabled=True).all()

        print(f"\n{'='*80}")
        print(f"TESTING {len(patterns)} SKIP PATTERNS:")
        print(f"{'='*80}\n")

        matches = []
        for pattern in patterns:
            pattern_str = pattern.pattern

            if pattern.is_regex:
                try:
                    # Test regex pattern
                    regex = re.compile(pattern_str, re.DOTALL | re.IGNORECASE)
                    match = regex.search(message_text)

                    if match:
                        matched_text = match.group(0)
                        matches.append({
                            'id': pattern.id,
                            'type': 'REGEX',
                            'pattern': pattern_str[:100],
                            'matched': matched_text[:200],
                            'full_pattern': pattern_str
                        })
                        print(f"✅ MATCH [ID {pattern.id}] REGEX")
                        print(f"   Pattern: {pattern_str[:100]}...")
                        print(f"   Matched: {matched_text[:200]}...")
                        print()
                except Exception as e:
                    print(f"⚠️  [ID {pattern.id}] Regex error: {e}")
            else:
                # Test plain text pattern
                if pattern_str in message_text:
                    matches.append({
                        'id': pattern.id,
                        'type': 'TEXT',
                        'pattern': pattern_str[:100],
                        'matched': pattern_str[:200],
                        'full_pattern': pattern_str
                    })
                    print(f"✅ MATCH [ID {pattern.id}] TEXT")
                    print(f"   Pattern: {pattern_str[:100]}...")
                    print()

        # Now apply all filters and show result
        print(f"\n{'='*80}")
        print(f"FILTERING RESULT:")
        print(f"{'='*80}")

        filtered_text = message_text
        for pattern in patterns:
            if pattern.is_regex:
                try:
                    regex = re.compile(pattern.pattern, re.DOTALL | re.IGNORECASE)
                    filtered_text = regex.sub('', filtered_text)
                except:
                    pass
            else:
                filtered_text = filtered_text.replace(pattern.pattern, '')

        # Clean up whitespace
        filtered_text = re.sub(r'\s+', ' ', filtered_text).strip()

        print(f"\nFILTERED MESSAGE TEXT ({len(filtered_text)} chars):")
        print("-" * 80)
        print(filtered_text)
        print("-" * 80)

        print(f"\n{'='*80}")
        print(f"SUMMARY:")
        print(f"  Original length: {len(message_text)} chars")
        print(f"  Filtered length: {len(filtered_text)} chars")
        print(f"  Removed: {len(message_text) - len(filtered_text)} chars")
        print(f"  Patterns matched: {len(matches)}")

        if len(filtered_text) < 50:
            print(f"\n⚠️  WARNING: Message almost completely filtered out!")
            print(f"\n🔍 MATCHING PATTERNS:")
            for m in matches:
                print(f"\n  [{m['id']}] {m['type']}")
                print(f"      Pattern: {m['pattern']}")
                if len(m['matched']) > 100:
                    print(f"      Matched: {m['matched'][:100]}... ({len(m['matched'])} chars)")
                else:
                    print(f"      Matched: {m['matched']}")

        print(f"{'='*80}\n")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 diagnose_filter.py <ticket_number> [message_date]")
        print("Example: python3 diagnose_filter.py DE25007155")
        print("Example: python3 diagnose_filter.py DE25007155 '2025-10-20'")
        sys.exit(1)

    ticket_number = sys.argv[1]
    message_date = sys.argv[2] if len(sys.argv) > 2 else None

    success = diagnose_message_filtering(ticket_number, message_date)
    sys.exit(0 if success else 1)
