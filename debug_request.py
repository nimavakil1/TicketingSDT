#!/usr/bin/env python3
"""
Debug script to capture exact HTTP request being sent
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import requests
import os
from datetime import datetime, timezone
import random
import string
import json

# Enable detailed HTTP logging
import logging
import http.client as http_client
http_client.HTTPConnection.debuglevel = 1
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

print("\n" + "="*70)
print("DEBUG: Capturing exact HTTP request")
print("="*70 + "\n")

# Get credentials
base_url = os.getenv('TICKETING_API_BASE_URL', 'https://api.distri-smart.com/api/sdt/1')
username = os.getenv('TICKETING_API_USERNAME', 'TicketingAgent')
password = os.getenv('TICKETING_API_PASSWORD')

print(f"Base URL: {base_url}")
print(f"Username: {username}")
print(f"Password: {'*' * len(password) if password else 'NOT SET'}")
print()

# Step 1: Authenticate
print("="*70)
print("STEP 1: Authentication Request")
print("="*70)
auth_url = f"{base_url}/Account/login"
auth_data = {
    'username': username,
    'password': password
}
print(f"URL: {auth_url}")
print(f"Data: {json.dumps(auth_data, indent=2)}")
print("\nSending authentication request...\n")

session = requests.Session()
auth_response = session.post(auth_url, json=auth_data, timeout=30)

print(f"\nAuth Response Status: {auth_response.status_code}")
print(f"Auth Response Headers: {dict(auth_response.headers)}")
auth_result = auth_response.json()
print(f"Auth Response Body: {json.dumps(auth_result, indent=2)}")

token = auth_result.get('access_token')
if not token:
    print("\n❌ Authentication failed - no access_token in response!")
    print(f"Response: {json.dumps(auth_result, indent=2)}")
    sys.exit(1)

print(f"\n✅ Got token: {token[:20]}...")

# Step 2: UpsertTicket
print("\n" + "="*70)
print("STEP 2: UpsertTicket Request")
print("="*70)

# Generate data
current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f") + " +00:00"
gmail_thread_id = ''.join(random.choices(string.digits, k=16))

upsert_url = f"{base_url}/tickets/tickets/UpsertTicket"
print(f"URL: {upsert_url}")
print(f"\nHeaders:")
print(f"  Authorization: Bearer {token[:20]}...")
print(f"\nForm Data:")

form_data = {
    'SalesOrderReference': '028-1374358-5033950',
    'TicketTypeId': 2,
    'ContactName': 'Customer Support Test',
    'Comment': 'Test ticket creation via API',
    'EntranceEmailBody': 'Customer inquiry about order status',
    'EntranceEmailDate': current_time,
    'EntranceEmailSubject': 'Order Status Inquiry',
    'EntranceEmailSenderAddress': 'customer@example.com',
    'EntranceGmailThreadId': gmail_thread_id
}

for key, value in form_data.items():
    print(f"  {key}: {value} (type: {type(value).__name__})")

print("\n" + "-"*70)
print("IMPORTANT: Check if TicketTypeId is being sent as integer or string")
print("-"*70)

# Set headers
headers = {
    'Authorization': f'Bearer {token}'
}

# Force multipart/form-data
files_param = [('', ('', ''))]

print("\nSending UpsertTicket request...\n")
print("Using files parameter to force multipart/form-data encoding")
print(f"files_param: {files_param}\n")

try:
    response = session.post(
        upsert_url,
        data=form_data,
        files=files_param,
        headers=headers,
        timeout=30
    )

    print(f"\n" + "="*70)
    print("Response:")
    print("="*70)
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print(f"\nBody:")

    if response.status_code == 200:
        result = response.json()
        print(json.dumps(result, indent=2))

        if result.get('succeeded'):
            print(f"\n✅ SUCCESS! Ticket ID: {result.get('id')}")
        else:
            print(f"\n❌ FAILED")
            messages = result.get('messages', [])
            for msg in messages:
                print(f"  Error: {msg.get('messageDescription', 'Unknown error')}")
    else:
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
