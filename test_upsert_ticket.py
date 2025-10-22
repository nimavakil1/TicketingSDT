#!/usr/bin/env python3
"""
Test script for creating a ticket via UpsertTicket API
"""
import os
import sys
import json
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from src.api.ticketing_client import TicketingAPIClient, TicketingAPIError
import structlog

# Configure logging
logging.basicConfig(level=logging.INFO)
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

    # Debug: Check environment variables
    import os
    print(f"\nDebug - Environment variables:")
    print(f"  TICKETING_API_BASE_URL: {os.getenv('TICKETING_API_BASE_URL', 'NOT SET')}")
    print(f"  TICKETING_API_USERNAME: {os.getenv('TICKETING_API_USERNAME', 'NOT SET')}")
    password = os.getenv('TICKETING_API_PASSWORD')
    if password:
        print(f"  TICKETING_API_PASSWORD: {'*' * len(password)} (length: {len(password)})")
    else:
        print(f"  TICKETING_API_PASSWORD: NOT SET")

    print(f"\nDebug - .env file check:")
    env_path = Path.cwd() / '.env'
    print(f"  Looking for: {env_path}")
    print(f"  File exists: {env_path.exists()}")
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                if 'TICKETING_API' in line and not line.strip().startswith('#'):
                    # Mask password
                    if 'PASSWORD' in line:
                        print(f"  Found: TICKETING_API_PASSWORD=*** (masked)")
                    else:
                        print(f"  Found: {line.strip()}")

    try:
        # Initialize the API client
        print("\n[1/4] Initializing API client...")
        client = TicketingAPIClient()

        # First, check if order exists
        print(f"\n[2/4] Checking if order exists in system...")
        try:
            existing_ticket = client.get_ticket_by_ticket_number(amazon_order_number)
            if existing_ticket:
                print(f"  ✓ Found existing ticket(s) for this order:")
                print(f"    {json.dumps(existing_ticket, indent=4, default=str)[:500]}...")
            else:
                print(f"  ℹ No existing ticket found for this order (this is normal for new orders)")
        except Exception as e:
            print(f"  ⚠ Could not check for existing ticket: {e}")

        # Create/update the ticket
        print(f"\n[3/4] Creating ticket in old system...")
        print(f"  - Order Number: {amazon_order_number}")
        print(f"  - Ticket Type: 2 (Tracking)")
        print(f"  - Contact Name: Test Customer")

        # Try with ONLY required fields first
        print(f"\nAttempt 1: Minimal fields (required only)")
        response = client.upsert_ticket(
            sales_order_reference=amazon_order_number,
            ticket_type_id=2,  # Tracking
            contact_name="Customer Name"
        )

        if response.get('succeeded'):
            print("  ✓ Success with minimal fields!")
        else:
            print("  ✗ Failed with minimal fields, trying with all optional fields...")

            # Try again with ALL optional fields including date
            from datetime import datetime, timezone
            # Format with 6 digits for microseconds (not 3 for milliseconds)
            current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f") + " +00:00"

            print(f"\nAttempt 2: With ALL optional fields (including date)")
            print(f"  EntranceEmailDate: {current_time}")
            print(f"  (6 digits for microseconds)")

            response = client.upsert_ticket(
                sales_order_reference=amazon_order_number,
                ticket_type_id=2,  # Tracking
                contact_name="Customer Name",
                comment="Test ticket created via API",
                entrance_email_subject="Test: Tracking inquiry",
                entrance_email_body="Customer is asking about shipment tracking.",
                entrance_email_sender_address="test@example.com",
                entrance_email_date=current_time
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
                print(f"\n[4/4] Fetching ticket details for: {ticket_number}")
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
                print(f"\n[4/4] Fetching ticket by Amazon order: {amazon_order_number}")
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
    sys.exit(test_upsert_ticket())
