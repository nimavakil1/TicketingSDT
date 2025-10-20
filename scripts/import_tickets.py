#!/usr/bin/env python3
"""
Import specific tickets from old ticketing system
WITHOUT running AI analysis (manual testing mode)
"""
import sys
import os
from pathlib import Path
from typing import List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from src.api.ticketing_client import TicketingAPIClient, TicketingAPIError
from src.database.db import SessionLocal
from src.database.models import TicketState, ProcessedEmail
import structlog

logger = structlog.get_logger(__name__)


def import_ticket(ticket_number: str, session, ticketing_client: TicketingAPIClient) -> bool:
    """
    Import a single ticket from old system without AI analysis

    Args:
        ticket_number: Ticket number to import
        session: Database session
        ticketing_client: API client

    Returns:
        True if successful
    """
    try:
        print(f"\n📥 Importing ticket {ticket_number}...")

        # Fetch ticket from old system
        tickets = ticketing_client.get_ticket_by_ticket_number(ticket_number)

        if not tickets:
            print(f"  ❌ Ticket {ticket_number} not found")
            return False

        ticket_data = tickets[0]

        # Check if already exists
        existing = session.query(TicketState).filter_by(
            ticket_number=ticket_number
        ).first()

        if existing:
            print(f"  ⚠️  Ticket {ticket_number} already exists in database")
            return False

        # Extract sales order data
        sales_order = ticket_data.get('salesOrder', {})

        # Create ticket state with correct field mappings (WITHOUT AI analysis)
        ticket_state = TicketState(
            ticket_number=ticket_number,
            ticket_id=ticket_data.get('id'),
            order_number=sales_order.get('salesId'),
            customer_name=ticket_data.get('contactName'),
            customer_email=sales_order.get('confirmedEmail'),
            customer_language=ticket_data.get('customerLanguageCultureName', 'de-DE'),
            customer_address=None,  # Not in response
            customer_city=None,
            customer_postal_code=None,
            customer_country=None,
            customer_phone=None,
            supplier_name=None,  # Not in this endpoint
            supplier_email=None,
            purchase_order_number=sales_order.get('purchaseOrderNumber'),
            tracking_number=None,  # Not in response
            carrier_name=None,
            ticket_type_id=ticket_data.get('ticketTypeId'),
            ticket_status_id=ticket_data.get('ticketStatusId'),
            owner_id=None,  # Not in response
            current_state='imported',  # Mark as manually imported
            product_details=str(sales_order.get('salesLines', [])),
            order_total=sales_order.get('salesBalanceMST'),
            order_currency=sales_order.get('currencyCode'),
            order_date=sales_order.get('confirmedDate')
        )

        session.add(ticket_state)
        session.flush()

        # Import messages from ticketDetails
        ticket_details = ticket_data.get('ticketDetails', [])
        message_count = 0

        for detail in ticket_details:
            # Create a unique identifier for each message
            detail_id = detail.get('id') or detail.get('recId')
            if not detail_id:
                continue

            msg_id = f"imported_{ticket_number}_{detail_id}"

            # Check if already exists
            existing_msg = session.query(ProcessedEmail).filter_by(gmail_message_id=msg_id).first()
            if existing_msg:
                continue

            # Create ProcessedEmail entry
            processed_email = ProcessedEmail(
                gmail_message_id=msg_id,
                gmail_thread_id=ticket_data.get('entranceGmailThreadId'),
                ticket_id=ticket_state.id,
                order_number=sales_order.get('salesId'),
                subject=detail.get('subject') or ticket_data.get('entranceEmailSubject'),
                from_address=detail.get('senderEmail') or ticket_data.get('entranceEmailSenderAddress'),
                success=True
            )
            session.add(processed_email)
            message_count += 1

        print(f"  ✅ Imported {ticket_number} with {message_count} messages")
        print(f"     Customer: {ticket_data.get('contactName')}")
        print(f"     Order: {sales_order.get('salesId')}")
        print(f"     Status: No AI analysis (manual mode)")

        return True

    except TicketingAPIError as e:
        print(f"  ❌ API Error: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        logger.error(f"Failed to import ticket", ticket_number=ticket_number, error=str(e))
        return False


def import_tickets(ticket_numbers: List[str]):
    """Import multiple tickets"""
    session = SessionLocal()
    ticketing_client = TicketingAPIClient()

    try:
        print(f"\n🎯 Importing {len(ticket_numbers)} tickets...")
        print("⚠️  AI analysis will NOT run automatically (manual mode)\n")

        success_count = 0
        fail_count = 0

        for ticket_number in ticket_numbers:
            if import_ticket(ticket_number, session, ticketing_client):
                success_count += 1
            else:
                fail_count += 1

        session.commit()

        print(f"\n" + "="*60)
        print(f"✅ Successfully imported: {success_count}/{len(ticket_numbers)}")
        if fail_count > 0:
            print(f"❌ Failed: {fail_count}")
        print(f"📌 All tickets are in manual mode (no AI analysis)")
        print("="*60)

        return success_count > 0

    except Exception as e:
        session.rollback()
        print(f"\n❌ Import failed: {e}")
        return False
    finally:
        session.close()


if __name__ == '__main__':
    # Ticket numbers to import
    TICKETS_TO_IMPORT = [
        'FR25005137',
        'DE25007159',
        'DE25007156',
        'DE25007155',
        'DE25007154',
        'AT25005134',
        'DE25006906'
    ]

    success = import_tickets(TICKETS_TO_IMPORT)
    sys.exit(0 if success else 1)
