#!/usr/bin/env python3
"""
Script to list all tickets currently in the database
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database.models import TicketState, init_database

def list_tickets():
    """List all tickets in the database"""
    SessionMaker = init_database()
    session = SessionMaker()

    try:
        tickets = session.query(TicketState).order_by(TicketState.updated_at.desc()).all()

        if not tickets:
            print("No tickets found in database")
            return

        print(f"\nTotal tickets: {len(tickets)}\n")
        print(f"{'Ticket Number':<15} {'Order Number':<20} {'State':<20} {'Last Updated'}")
        print("-" * 85)

        for ticket in tickets:
            print(f"{ticket.ticket_number:<15} {ticket.order_number or 'N/A':<20} {ticket.current_state or 'N/A':<20} {ticket.updated_at}")

        # Print just the ticket numbers for easy copying
        print("\n" + "="*80)
        print("Ticket numbers only:")
        print("="*80)
        for ticket in tickets:
            print(ticket.ticket_number)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == '__main__':
    list_tickets()
