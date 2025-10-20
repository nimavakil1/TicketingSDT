#!/bin/bash
# Wrapper script to import tickets with correct Python path

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

from src.api.ticketing_client import TicketingAPIClient, TicketingAPIError
from src.database import init_database, TicketState

# Initialize database
SessionMaker = init_database()
SessionLocal = SessionMaker

def import_ticket(ticket_number, session, ticketing_client):
    """Import a single ticket without AI analysis"""
    try:
        print(f"\n📥 Importing ticket {ticket_number}...")

        tickets = ticketing_client.get_ticket_by_ticket_number(ticket_number)

        if not tickets:
            print(f"  ❌ Ticket {ticket_number} not found")
            return False

        ticket_data = tickets[0]

        # Debug: print ticket data structure
        print(f"  📋 Ticket data keys: {list(ticket_data.keys())}")
        print(f"  📋 Sample data: {str(ticket_data)[:500]}")

        # Check if exists
        existing = session.query(TicketState).filter_by(ticket_number=ticket_number).first()
        if existing:
            print(f"  ⚠️  Already exists")
            return False

        # Create ticket
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
            current_state='imported',
            product_details=str(ticket_data.get('items', [])),
            order_total=ticket_data.get('orderTotal'),
            order_currency=ticket_data.get('orderCurrency'),
            order_date=ticket_data.get('orderDate')
        )

        session.add(ticket_state)
        session.flush()

        # Messages are already in ticket_data
        messages = ticket_data.get('messages', [])
        msg_count = len(messages) if messages else 0

        print(f"  ✅ Imported with {msg_count} messages")
        print(f"     Customer: {ticket_data.get('customerName')}")
        print(f"     Order: {ticket_data.get('orderNumber')}")

        return True

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

# Main
session = SessionLocal()
ticketing_client = TicketingAPIClient()

tickets = [
    'FR25005137',
    'DE25007159',
    'DE25007156',
    'DE25007155',
    'DE25007154',
    'AT25005134',
    'DE25006906'
]

print(f"\n🎯 Importing {len(tickets)} tickets (NO AI analysis)...\n")

success = 0
for ticket in tickets:
    if import_ticket(ticket, session, ticketing_client):
        success += 1

session.commit()
session.close()

print(f"\n{'='*60}")
print(f"✅ Successfully imported: {success}/{len(tickets)}")
print(f"📌 All tickets in manual mode")
print(f"{'='*60}\n")

PYTHON_SCRIPT
