#!/usr/bin/env python3
"""
Check if UI has data to display
Diagnoses why UI pages might be empty
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.models import init_database, ProcessedEmail, TicketState, AIDecisionLog, PendingEmailRetry
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)

def check_database():
    """Check database contents"""
    print("=" * 60)
    print("DATABASE CONTENTS CHECK")
    print("=" * 60)

    Session = init_database()
    session = Session()

    try:
        # Check ProcessedEmail
        email_count = session.query(ProcessedEmail).count()
        print(f"\n📧 ProcessedEmail records: {email_count}")

        if email_count > 0:
            print("\nRecent emails:")
            emails = session.query(ProcessedEmail).order_by(
                ProcessedEmail.processed_at.desc()
            ).limit(5).all()

            for email in emails:
                success = getattr(email, 'success', 'N/A')
                error = getattr(email, 'error_message', None)
                print(f"  - ID: {email.id}")
                print(f"    Subject: {email.subject[:50] if email.subject else 'N/A'}")
                print(f"    From: {email.from_address}")
                print(f"    Processed: {email.processed_at}")
                print(f"    Success: {success}")
                if error:
                    print(f"    Error: {error[:100]}")
                print()

        # Check TicketState
        ticket_count = session.query(TicketState).count()
        print(f"\n🎫 TicketState records: {ticket_count}")

        if ticket_count > 0:
            print("\nRecent tickets:")
            tickets = session.query(TicketState).order_by(
                TicketState.updated_at.desc()
            ).limit(5).all()

            for ticket in tickets:
                print(f"  - Ticket: {ticket.ticket_number}")
                print(f"    State: {ticket.current_state}")
                print(f"    Customer: {ticket.customer_email}")
                print(f"    Updated: {ticket.updated_at}")
                print(f"    Escalated: {ticket.escalated}")
                print()

        # Check AIDecisionLog
        decision_count = session.query(AIDecisionLog).count()
        print(f"\n🤖 AIDecisionLog records: {decision_count}")

        if decision_count > 0:
            print("\nRecent AI decisions:")
            decisions = session.query(AIDecisionLog).order_by(
                AIDecisionLog.timestamp.desc()
            ).limit(5).all()

            for dec in decisions:
                print(f"  - ID: {dec.id}")
                print(f"    Intent: {dec.detected_intent}")
                print(f"    Confidence: {dec.confidence_score}")
                print(f"    Action: {dec.action_taken}")
                print(f"    Time: {dec.timestamp}")
                print()

        # Check PendingEmailRetry
        retry_count = session.query(PendingEmailRetry).count()
        print(f"\n🔄 PendingEmailRetry records: {retry_count}")

        # Today's stats
        print("\n" + "=" * 60)
        print("TODAY'S STATS")
        print("=" * 60)

        today = datetime.utcnow().date()
        emails_today = session.query(ProcessedEmail).filter(
            ProcessedEmail.processed_at >= today
        ).count()

        decisions_today = session.query(AIDecisionLog).filter(
            AIDecisionLog.timestamp >= today
        ).count()

        print(f"\n📊 Emails processed today: {emails_today}")
        print(f"📊 AI decisions today: {decisions_today}")

        # Check for schema issues
        print("\n" + "=" * 60)
        print("SCHEMA VERIFICATION")
        print("=" * 60)

        if email_count > 0:
            sample_email = session.query(ProcessedEmail).first()
            has_success = hasattr(sample_email, 'success')
            has_error_msg = hasattr(sample_email, 'error_message')

            print(f"\n✓ ProcessedEmail has 'success' field: {has_success}")
            print(f"✓ ProcessedEmail has 'error_message' field: {has_error_msg}")

            if not has_success or not has_error_msg:
                print("\n⚠️  WARNING: Database migration needed!")
                print("   Run: python3 scripts/migrate_add_success_tracking.py")

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        if email_count == 0 and ticket_count == 0:
            print("\n❌ ISSUE: Database is empty!")
            print("   The agent hasn't processed any emails yet.")
            print("   Send a test email to trigger processing.")
        elif email_count > 0 and ticket_count == 0:
            print("\n⚠️  WARNING: Emails processed but no tickets created")
            print("   This might be normal if emails couldn't be linked to tickets.")
        elif email_count > 0 and decision_count == 0:
            print("\n⚠️  WARNING: No AI decisions logged")
            print("   Check if AI analysis is working correctly.")
        else:
            print("\n✅ Database has data - UI should be able to display it!")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    check_database()
