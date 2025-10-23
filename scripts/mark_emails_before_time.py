#!/usr/bin/env python3
"""
Mark all Gmail emails before a specified time as already processed.
This allows starting the AI agent from a specific point in time.

Usage:
    python scripts/mark_emails_before_time.py "2025-10-23 14:30:00"

The time should be in CET (Central European Time).
"""

import sys
from datetime import datetime, timezone
import pytz
from sqlalchemy.orm import Session

# Add parent directory to path
sys.path.insert(0, '/home/ai/TicketingSDT')

from src.email.gmail_monitor import GmailMonitor
from src.database.models import ProcessedEmail, init_database
from config.settings import settings

def mark_emails_before_time(cutoff_time_cet: str):
    """
    Mark all emails before the specified time as already processed.

    Args:
        cutoff_time_cet: Time in CET format "YYYY-MM-DD HH:MM:SS"
    """
    # Parse CET time
    cet = pytz.timezone('CET')
    try:
        cutoff_dt = datetime.strptime(cutoff_time_cet, "%Y-%m-%d %H:%M:%S")
        cutoff_dt = cet.localize(cutoff_dt)
    except ValueError:
        print(f"Error: Invalid time format. Use: YYYY-MM-DD HH:MM:SS")
        print(f"Example: 2025-10-23 14:30:00")
        sys.exit(1)

    # Convert to UTC for Gmail API
    cutoff_dt_utc = cutoff_dt.astimezone(pytz.UTC)
    cutoff_epoch = int(cutoff_dt_utc.timestamp())

    print(f"Cutoff time (CET): {cutoff_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Cutoff time (UTC): {cutoff_dt_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Epoch timestamp: {cutoff_epoch}")
    print()

    # Initialize Gmail monitor
    print("Connecting to Gmail...")
    try:
        gmail = GmailMonitor()
    except Exception as e:
        print(f"Error connecting to Gmail: {e}")
        print("Make sure Gmail API credentials are set up correctly.")
        sys.exit(1)

    # Fetch all emails before cutoff time
    print(f"Fetching emails before {cutoff_time_cet} CET...")

    try:
        # Build query for emails before cutoff time in inbox
        query = f'in:inbox before:{cutoff_epoch}'

        results = gmail.service.users().messages().list(
            userId='me',
            q=query,
            maxResults=500  # Gmail API limit
        ).execute()

        messages = results.get('messages', [])

        # Check if there are more messages
        next_page_token = results.get('nextPageToken')

        if next_page_token:
            print(f"Warning: Found more than 500 emails. This script will process the first 500.")
            print(f"You may need to run it multiple times or adjust the cutoff time.")

        if not messages:
            print("No emails found before this time.")
            return

        print(f"Found {len(messages)} emails to mark as processed.")
        print()

        # Ask for confirmation
        response = input(f"Mark {len(messages)} emails as processed? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Cancelled.")
            return

        # Initialize database
        SessionMaker = init_database()
        session = SessionMaker()

        # Mark emails as processed
        marked_count = 0
        skipped_count = 0

        for msg in messages:
            gmail_message_id = msg['id']

            # Check if already in database
            existing = session.query(ProcessedEmail).filter_by(
                gmail_message_id=gmail_message_id
            ).first()

            if existing:
                skipped_count += 1
                continue

            # Add to database as processed
            processed_email = ProcessedEmail(
                gmail_message_id=gmail_message_id,
                processed_at=datetime.utcnow(),
                success=True,
                subject="[Marked as processed before cutoff]",
                from_address="system",
                message_body="",
                error_message="Marked as processed via mark_emails_before_time.py"
            )
            session.add(processed_email)
            marked_count += 1

            # Commit in batches of 50
            if marked_count % 50 == 0:
                session.commit()
                print(f"Marked {marked_count} emails...")

        # Final commit
        session.commit()
        session.close()

        print()
        print(f"✓ Successfully marked {marked_count} emails as processed")
        print(f"✓ Skipped {skipped_count} emails (already in database)")
        print()
        print("The AI agent will now only process emails after:")
        print(f"  {cutoff_time_cet} CET")
        print(f"  {cutoff_dt_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/mark_emails_before_time.py \"YYYY-MM-DD HH:MM:SS\"")
        print("Example: python scripts/mark_emails_before_time.py \"2025-10-23 14:30:00\"")
        print()
        print("Time should be in CET (Central European Time)")
        sys.exit(1)

    cutoff_time = sys.argv[1]
    mark_emails_before_time(cutoff_time)
