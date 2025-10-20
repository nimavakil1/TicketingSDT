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
from src.database import init_database, TicketState, ProcessedEmail
from sqlalchemy import text

# Initialize database
SessionMaker = init_database()
SessionLocal = SessionMaker

# Add message_body column if it doesn't exist
session = SessionLocal()
try:
    session.execute(text("ALTER TABLE processed_emails ADD COLUMN message_body TEXT"))
    session.commit()
    print("✓ Added message_body column to processed_emails")
except:
    pass  # Column already exists
finally:
    session.close()

def import_ticket(ticket_number, session, ticketing_client):
    """Import a single ticket without AI analysis"""
    try:
        print(f"\n📥 Importing ticket {ticket_number}...")

        tickets = ticketing_client.get_ticket_by_ticket_number(ticket_number)

        if not tickets:
            print(f"  ❌ Ticket {ticket_number} not found")
            return False

        ticket_data = tickets[0]

        # Check if exists
        existing = session.query(TicketState).filter_by(ticket_number=ticket_number).first()
        if existing:
            print(f"  ⚠️  Already exists")
            return False

        # Extract sales order data
        sales_order = ticket_data.get('salesOrder', {})

        # Create ticket with correct field mappings
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
            current_state='imported',
            product_details=str(sales_order.get('salesLines', [])),
            order_total=sales_order.get('salesBalanceMST'),
            order_currency=sales_order.get('currencyCode'),
            order_date=sales_order.get('confirmedDate')
        )

        session.add(ticket_state)
        session.flush()

        # Import messages from ticketDetails
        ticket_details = ticket_data.get('ticketDetails', [])
        msg_count = 0

        for detail in ticket_details:
            # Create a unique identifier for each message
            detail_id = detail.get('id')
            if not detail_id:
                continue

            msg_id = f"imported_{ticket_number}_{detail_id}"

            # Check if already exists
            existing_msg = session.query(ProcessedEmail).filter_by(gmail_message_id=msg_id).first()
            if existing_msg:
                continue

            # Extract message content and metadata
            comment = detail.get('comment', '')
            entrance_body = detail.get('entranceEmailBody', '')
            message_body = entrance_body if entrance_body else comment

            # Determine source/target for subject line
            source = detail.get('sourceTicketSideTypeId')
            target = detail.get('targetTicketSideTypeId')

            if source == 2 and target == 1:
                subject = "Message from customer"
            elif source == 1 and target == 2:
                subject = "Message to customer"
            elif source == 1 and target == 3:
                subject = "Message to supplier"
            elif source == 3 and target == 1:
                subject = "Message from supplier"
            elif source == 1 and target == 1:
                subject = "Internal note"
            else:
                subject = "Message"

            # Create ProcessedEmail entry with message body
            session.execute(text("""
                INSERT INTO processed_emails
                (gmail_message_id, gmail_thread_id, ticket_id, order_number, subject, from_address, message_body, success, processed_at)
                VALUES (:msg_id, :thread_id, :ticket_id, :order_num, :subject, :from_addr, :body, 1, :created)
            """), {
                'msg_id': msg_id,
                'thread_id': str(ticket_data.get('entranceGmailThreadId')),
                'ticket_id': ticket_state.id,
                'order_num': sales_order.get('salesId'),
                'subject': subject,
                'from_addr': detail.get('receiverEmailAddress') or ticket_data.get('entranceEmailSenderAddress'),
                'body': message_body,
                'created': detail.get('createdDateTime')
            })
            msg_count += 1

        print(f"  ✅ Imported with {msg_count} messages")
        print(f"     Customer: {ticket_data.get('contactName')}")
        print(f"     Order: {sales_order.get('salesId')}")

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
