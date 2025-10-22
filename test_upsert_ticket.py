#!/usr/bin/env python3
"""
Test script for creating a ticket via UpsertTicket API
"""
import os
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.api.ticketing_client import TicketingAPIClient, TicketingAPIError
import structlog

# Configure logging
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)

logger = structlog.get_logger(__name__)

def test_upsert_ticket():
    """Test creating a ticket with the provided Amazon order number"""

    # Amazon order number from user
    amazon_order_number = "408-1508747-7774717"

    print(f"\n{'='*70}")
    print(f"Testing UpsertTicket API")
    print(f"{'='*70}")
    print(f"Amazon Order Number: {amazon_order_number}")

    try:
        # Initialize the API client
        print("\n[1/3] Initializing API client...")
        client = TicketingAPIClient()

        # Create/update the ticket
        print(f"[2/3] Creating ticket in old system...")
        print(f"  - Order Number: {amazon_order_number}")
        print(f"  - Ticket Type: 2 (Tracking)")
        print(f"  - Contact Name: Test Customer")

        response = client.upsert_ticket(
            sales_order_reference=amazon_order_number,
            ticket_type_id=2,  # Tracking
            contact_name="Test Customer",
            comment="Test ticket created via API",
            entrance_email_subject="Test: Tracking inquiry",
            entrance_email_body="Customer is asking about shipment tracking.",
            entrance_email_sender_address="test@example.com"
        )

        print(f"\n{'='*70}")
        print("UpsertTicket Response:")
        print(f"{'='*70}")
        print(json.dumps(response, indent=2))

        # Check if succeeded
        if response.get('succeeded'):
            ticket_id = response.get('id')
            print(f"\n✅ SUCCESS! Ticket created/updated with ID: {ticket_id}")

            # Extract ticket number from messages or dataItems
            ticket_number = None

            # Check dataItems for ticket number
            data_items = response.get('dataItems', [])
            if data_items:
                print(f"\nData Items: {data_items}")
                # The ticket number might be in dataItems
                if isinstance(data_items, list) and len(data_items) > 0:
                    first_item = data_items[0]
                    if isinstance(first_item, dict):
                        ticket_number = first_item.get('ticketNumber') or first_item.get('TicketNumber')

            # Check viewString for ticket number (format: DE25XXXXXX)
            view_string = response.get('viewString', '')
            if view_string and 'DE25' in view_string:
                import re
                match = re.search(r'DE25\d+', view_string)
                if match:
                    ticket_number = match.group(0)

            if ticket_number:
                print(f"\n[3/3] Fetching ticket details for: {ticket_number}")
                ticket_details = client.get_ticket_by_ticket_number(ticket_number)

                if ticket_details:
                    print(f"\n{'='*70}")
                    print("Ticket Details:")
                    print(f"{'='*70}")
                    print(json.dumps(ticket_details, indent=2, default=str))
                else:
                    print(f"\n⚠️  Could not fetch ticket details for {ticket_number}")
            else:
                print(f"\n⚠️  Ticket created but ticket number not found in response")
                print(f"Try fetching by Amazon order number instead...")

                # Try to fetch by Amazon order number
                print(f"\n[3/3] Fetching ticket by Amazon order: {amazon_order_number}")
                ticket_details = client.get_ticket_by_ticket_number(amazon_order_number)

                if ticket_details:
                    print(f"\n{'='*70}")
                    print("Ticket Details:")
                    print(f"{'='*70}")
                    print(json.dumps(ticket_details, indent=2, default=str))
                else:
                    print(f"\n⚠️  Could not fetch ticket by order number either")
                    print(f"The ticket was created but we need to find the ticket number manually")
                    print(f"Check the old system UI with order: {amazon_order_number}")
        else:
            print(f"\n❌ FAILED! Ticket creation failed")
            messages = response.get('messages', [])
            if messages:
                print("\nError messages:")
                for msg in messages:
                    print(f"  - {msg.get('messageCode')}: {msg.get('messageDescription')}")

    except TicketingAPIError as e:
        print(f"\n❌ API Error: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print(f"\n{'='*70}")
    return 0

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    sys.exit(test_upsert_ticket())
