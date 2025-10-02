#!/usr/bin/env python3
"""
Supplier Management Utility
Command-line tool for managing supplier contacts
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.database.models import init_database, Supplier
import json


def list_suppliers(session):
    """List all suppliers"""
    suppliers = session.query(Supplier).all()

    if not suppliers:
        print("No suppliers found.")
        return

    print(f"\n{'ID':<5} {'Name':<30} {'Default Email':<40}")
    print("=" * 75)

    for supplier in suppliers:
        print(f"{supplier.id:<5} {supplier.name:<30} {supplier.default_email:<40}")

        if supplier.contact_fields:
            for field, email in supplier.contact_fields.items():
                print(f"      └─ {field}: {email}")

    print()


def add_supplier(session, name, default_email, contacts_json=None):
    """Add a new supplier"""
    # Check if already exists
    existing = session.query(Supplier).filter_by(name=name).first()
    if existing:
        print(f"Error: Supplier '{name}' already exists (ID: {existing.id})")
        return

    # Parse contact fields
    contact_fields = {}
    if contacts_json:
        try:
            contact_fields = json.loads(contacts_json)
        except json.JSONDecodeError:
            print("Error: Invalid JSON for contact fields")
            return

    # Create supplier
    supplier = Supplier(
        name=name,
        default_email=default_email,
        contact_fields=contact_fields
    )

    session.add(supplier)
    session.commit()

    print(f"✓ Supplier '{name}' added successfully (ID: {supplier.id})")


def update_supplier(session, supplier_id, name=None, default_email=None, contacts_json=None):
    """Update an existing supplier"""
    supplier = session.query(Supplier).get(supplier_id)

    if not supplier:
        print(f"Error: Supplier ID {supplier_id} not found")
        return

    if name:
        supplier.name = name

    if default_email:
        supplier.default_email = default_email

    if contacts_json:
        try:
            supplier.contact_fields = json.loads(contacts_json)
        except json.JSONDecodeError:
            print("Error: Invalid JSON for contact fields")
            return

    session.commit()
    print(f"✓ Supplier ID {supplier_id} updated successfully")


def add_contact_field(session, supplier_id, field_name, email):
    """Add a contact field to a supplier"""
    supplier = session.query(Supplier).get(supplier_id)

    if not supplier:
        print(f"Error: Supplier ID {supplier_id} not found")
        return

    if not supplier.contact_fields:
        supplier.contact_fields = {}

    supplier.contact_fields[field_name] = email
    session.commit()

    print(f"✓ Added contact field '{field_name}' = '{email}' to supplier ID {supplier_id}")


def delete_supplier(session, supplier_id):
    """Delete a supplier"""
    supplier = session.query(Supplier).get(supplier_id)

    if not supplier:
        print(f"Error: Supplier ID {supplier_id} not found")
        return

    confirm = input(f"Are you sure you want to delete supplier '{supplier.name}' (ID: {supplier_id})? [y/N]: ")

    if confirm.lower() == 'y':
        session.delete(supplier)
        session.commit()
        print(f"✓ Supplier ID {supplier_id} deleted")
    else:
        print("Cancelled")


def main():
    parser = argparse.ArgumentParser(description="Manage supplier contacts")
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # List command
    subparsers.add_parser('list', help='List all suppliers')

    # Add command
    add_parser = subparsers.add_parser('add', help='Add a new supplier')
    add_parser.add_argument('name', help='Supplier name')
    add_parser.add_argument('email', help='Default email address')
    add_parser.add_argument('--contacts', help='Contact fields as JSON, e.g. \'{"returns": "returns@supplier.com"}\'')

    # Update command
    update_parser = subparsers.add_parser('update', help='Update a supplier')
    update_parser.add_argument('id', type=int, help='Supplier ID')
    update_parser.add_argument('--name', help='New name')
    update_parser.add_argument('--email', help='New default email')
    update_parser.add_argument('--contacts', help='New contact fields as JSON')

    # Add contact field command
    contact_parser = subparsers.add_parser('add-contact', help='Add a contact field')
    contact_parser.add_argument('id', type=int, help='Supplier ID')
    contact_parser.add_argument('field', help='Field name (e.g., returns, tracking)')
    contact_parser.add_argument('email', help='Email address')

    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a supplier')
    delete_parser.add_argument('id', type=int, help='Supplier ID')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize database
    Session = init_database()
    session = Session()

    try:
        if args.command == 'list':
            list_suppliers(session)

        elif args.command == 'add':
            add_supplier(session, args.name, args.email, args.contacts)

        elif args.command == 'update':
            update_supplier(session, args.id, args.name, args.email, args.contacts)

        elif args.command == 'add-contact':
            add_contact_field(session, args.id, args.field, args.email)

        elif args.command == 'delete':
            delete_supplier(session, args.id)

    finally:
        session.close()


if __name__ == '__main__':
    main()
