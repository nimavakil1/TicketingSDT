#!/usr/bin/env python3
"""
Capture and display the exact HTTP request being sent to UpsertTicket API
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

import requests
import logging

# Enable HTTP debugging
import http.client as http_client
http_client.HTTPConnection.debuglevel = 1

# Configure logging to capture all HTTP traffic
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

print("="*80)
print("CAPTURING EXACT HTTP REQUEST TO UpsertTicket API")
print("="*80)
print("\nThis will show the complete raw HTTP request including headers and body.\n")

# Import after logging is configured
from src.api.ticketing_client import TicketingAPIClient

# Test data
amazon_order_number = "408-1508747-7774717"

print(f"\nTest Parameters:")
print(f"  Amazon Order Number: {amazon_order_number}")
print(f"  Ticket Type: 2 (Tracking)")
print(f"  Contact Name: Customer Name")
print(f"  API Base URL: {os.getenv('TICKETING_API_BASE_URL')}")
print(f"  Username: {os.getenv('TICKETING_API_USERNAME')}")
print()
print("="*80)
print("AUTHENTICATION REQUEST:")
print("="*80)

try:
    client = TicketingAPIClient()

    print()
    print("="*80)
    print("UPSERT TICKET REQUEST:")
    print("="*80)
    print()

    # Make the request
    response = client.upsert_ticket(
        sales_order_reference=amazon_order_number,
        ticket_type_id=2,
        contact_name="Customer Name"
    )

    print()
    print("="*80)
    print("RESPONSE:")
    print("="*80)
    print()
    import json
    print(json.dumps(response, indent=2))

except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()

print()
print("="*80)
print("END OF CAPTURE")
print("="*80)
