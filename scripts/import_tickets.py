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
from src.database.models import TicketState
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

        # Create ticket state (WITHOUT AI analysis)
        ticket_state = TicketState(
            ticket_number=ticket_number,
            ticket_id=ticket_data.get('id'),
            order_number=ticket_data.get('orderNumber'),
            customer_name=ticket_data.get('customerName'),
            customer_email=ticket_data.get('customerEmail'),
            customer_language=ticket_data.get('customerLanguage', 'de-DE'),
            customer_address=ticket_data.get('customerAddress'),
            customer_city=ticket_data.get('customerCity'),
            customer_postal_code=ticket_data.get('customerPostalCode'),
            customer_country=ticket_data.get('customerCountry'),
            customer_phone=ticket_data.get('customerPhone'),
            supplier_name=ticket_data.get('supplierName'),
            supplier_email=ticket_data.get('supplierEmail'),
            purchase_order_number=ticket_data.get('purchaseOrderNumber'),
            tracking_number=ticket_data.get('trackingNumber'),
            carrier_name=ticket_data.get('carrierName'),
            ticket_type_id=ticket_data.get('typeId'),
            ticket_status_id=ticket_data.get('statusId'),
            owner_id=ticket_data.get('ownerId'),
            current_state='imported',  # Mark as manually imported
            product_details=str(ticket_data.get('items', [])),
            order_total=ticket_data.get('orderTotal'),
            order_currency=ticket_data.get('orderCurrency'),
            order_date=ticket_data.get('orderDate')
        )

        session.add(ticket_state)
        session.flush()

        # Fetch messages
        messages = ticketing_client.get_ticket_messages(ticket_number)
        message_count = len(messages) if messages else 0

        print(f"  ✅ Imported {ticket_number} with {message_count} messages")
        print(f"     Customer: {ticket_data.get('customerName')}")
        print(f"     Order: {ticket_data.get('orderNumber')}")
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
