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
from src.utils.text_filter import TextFilter
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

def import_ticket(ticket_number, session, ticketing_client, text_filter):
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

        # Extract shipping address
        import json
        shipping_address = {}
        try:
            shipping_payload = sales_order.get('shippingAddressPayload', '{}')
            shipping_data = json.loads(shipping_payload)
            shipping_address = shipping_data.get('ShippingAddress', {})
        except:
            pass

        # Extract supplier info from first purchase order
        purchase_orders = sales_order.get('purchaseOrders', [])
        supplier_name = None
        supplier_email = None
        purchase_order_number = None
        tracking_number = None
        tracking_url = None
        carrier_name = None

        if purchase_orders:
            first_po = purchase_orders[0]
            supplier_name = first_po.get('supplierName')
            purchase_order_number = first_po.get('orderNumber')

            # Extract tracking from deliveries
            deliveries = first_po.get('deliveries', [])
            if deliveries:
                parcels = deliveries[0].get('deliveryParcels', [])
                if parcels:
                    tracking_number = parcels[0].get('trackNumber')
                    tracking_url = parcels[0].get('traceUrl', '')
                    # Only use tracking if traceUrl is not empty
                    if not tracking_url:
                        tracking_number = None
                        tracking_url = None

                    shipment_method = parcels[0].get('shipmentMethod', {})
                    carrier_name = shipment_method.get('exportName')

        # Extract product details from salesOrderItems
        products = []
        for item in sales_order.get('salesOrderItems', []):
            products.append({
                'sku': item.get('productNumber'),
                'title': item.get('productTitle'),
                'quantity': item.get('quantity', 1),
                'price': item.get('singlePrice', 0)
            })

        # Create ticket with correct field mappings
        ticket_state = TicketState(
            ticket_number=ticket_number,
            ticket_id=ticket_data.get('id'),
            order_number=sales_order.get('orderNumber'),  # Use orderNumber not salesId
            customer_name=shipping_address.get('Name') or sales_order.get('customerName'),
            customer_email=sales_order.get('confirmedEmail'),
            customer_language=ticket_data.get('customerLanguageCultureName', 'de-DE'),
            customer_address=shipping_address.get('AddressLine1'),
            customer_city=shipping_address.get('City'),
            customer_postal_code=shipping_address.get('PostalCode'),
            customer_country=shipping_address.get('CountryCode'),
            customer_phone=shipping_address.get('Phone'),
            supplier_name=supplier_name,
            supplier_email=supplier_email,
            purchase_order_number=purchase_order_number,
            tracking_number=tracking_number,
            tracking_url=tracking_url,
            carrier_name=carrier_name,
            ticket_type_id=ticket_data.get('ticketTypeId'),
            ticket_status_id=ticket_data.get('ticketStatusId'),
            owner_id=None,  # Not in response
            current_state='imported',
            product_details=json.dumps(products),
            order_total=sales_order.get('totalPrice'),
            order_currency='EUR',
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
            raw_message_body = entrance_body if entrance_body else comment

            # Apply text filtering to remove skip blocks
            message_body = text_filter.filter_email_body(raw_message_body)

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
text_filter = TextFilter(session)

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
    if import_ticket(ticket, session, ticketing_client, text_filter):
        success += 1

session.commit()
session.close()

print(f"\n{'='*60}")
print(f"✅ Successfully imported: {success}/{len(tickets)}")
print(f"📌 All tickets in manual mode")
print(f"{'='*60}\n")

PYTHON_SCRIPT
