#!/usr/bin/env python3
"""
Show exactly what values are being sent in each field to UpsertTicket API
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

print("="*80)
print("UPSERT TICKET API - FIELD VALUES")
print("="*80)
print()

# Test data
amazon_order_number = "408-1508747-7774717"
ticket_type_id = 2
contact_name = "Customer Name"

print("Values being sent to UpsertTicket API:")
print("-" * 80)
print()

# Show each field
fields = {
    'SalesOrderReference': amazon_order_number,
    'TicketTypeId': ticket_type_id,
    'ContactName': contact_name,
}

print("REQUIRED FIELDS:")
print()
for field_name, field_value in fields.items():
    print(f"  {field_name}:")
    print(f"    Value: {repr(field_value)}")
    print(f"    Type:  {type(field_value).__name__}")
    if isinstance(field_value, str):
        print(f"    Length: {len(field_value)} characters")
        print(f"    Bytes: {field_value.encode('utf-8')}")
    print()

print("-" * 80)
print()
print("API ENDPOINT:")
print(f"  {os.getenv('TICKETING_API_BASE_URL')}/tickets/tickets/UpsertTicket")
print()
print("AUTHENTICATION:")
print(f"  Username: {os.getenv('TICKETING_API_USERNAME')}")
print(f"  Method: Bearer token (obtained via /Account/login)")
print()
print("CONTENT-TYPE:")
print(f"  multipart/form-data (with boundary)")
print()
print("="*80)
print()

# Now show what the actual HTTP request body looks like
print("SIMULATED MULTIPART BODY:")
print("-" * 80)
print()

boundary = "----WebKitFormBoundary1234567890"
body_parts = []

for field_name, field_value in fields.items():
    part = f"------WebKitFormBoundary1234567890\r\n"
    part += f'Content-Disposition: form-data; name="{field_name}"\r\n'
    part += f"\r\n"
    part += f"{field_value}\r\n"
    body_parts.append(part)

# Add empty file field (to force multipart)
body_parts.append(
    f"------WebKitFormBoundary1234567890\r\n"
    f'Content-Disposition: form-data; name=""; filename=""\r\n'
    f"\r\n"
    f"\r\n"
)

body_parts.append(f"------WebKitFormBoundary1234567890--\r\n")

full_body = "".join(body_parts)

print(full_body)
print()
print("-" * 80)
print()
print(f"Total body size: {len(full_body)} bytes")
print()
print("="*80)
