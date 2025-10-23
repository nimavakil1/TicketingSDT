#!/usr/bin/env python3
"""
Create ticket for order 405-8989219-6726713
Sends ALL fields as specified in API documentation
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from src.api.ticketing_client import TicketingAPIClient
from datetime import datetime, timezone
import random
import string
import json

print("\n" + "="*70)
print("Creating Ticket for Order: 405-8989219-6726713")
print("="*70 + "\n")

client = TicketingAPIClient()

# Generate current timestamp with 6 digits for microseconds
current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f") + " +00:00"

# Generate random gmail thread ID (16-digit number as string)
gmail_thread_id = ''.join(random.choices(string.digits, k=16))

print("Sending ALL fields as per API documentation:")
print(f"  SalesOrderReference: 405-8989219-6726713 (string, required)")
print(f"  TicketTypeId: 2 (int, required - Tracking)")
print(f"  ContactName: Customer Support Test (string, required)")
print(f"  Comment: Test ticket creation via API (string, optional)")
print(f"  EntranceEmailBody: Customer inquiry about order status (string, optional)")
print(f"  EntranceEmailDate: {current_time} (datetime, optional)")
print(f"  EntranceEmailSubject: Order Status Inquiry (string, optional)")
print(f"  EntranceEmailSenderAddress: customer@example.com (string, optional)")
print(f"  EntranceGmailThreadId: {gmail_thread_id} (string, optional)")
print(f"  Attachments: None (file, optional, multiple)")
print()

response = client.upsert_ticket(
    sales_order_reference="405-8989219-6726713",
    ticket_type_id=2,
    contact_name="Customer Support Test",
    comment="Test ticket creation via API",
    entrance_email_body="Customer inquiry about order status",
    entrance_email_date=current_time,
    entrance_email_subject="Order Status Inquiry",
    entrance_email_sender_address="customer@example.com",
    entrance_gmail_thread_id=gmail_thread_id
)

print("\n" + "="*70)
print("API Response:")
print("="*70)
print(json.dumps(response, indent=2))
print()

if response.get('succeeded'):
    print(f"✅ SUCCESS! Ticket ID: {response.get('id')}")
else:
    print(f"❌ FAILED")
    messages = response.get('messages', [])
    if messages:
        for msg in messages:
            print(f"  Error: {msg.get('messageDescription', 'Unknown error')}")
