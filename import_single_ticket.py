#!/usr/bin/env python3
"""
Script to import a single ticket by ticket number for testing
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

import structlog
from src.api.ticketing_client import TicketingAPIClient
from src.orchestrator import SupportAgentOrchestrator
from src.database.models import init_database

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger(__name__)

def import_ticket(ticket_number: str):
    """Import a single ticket by ticket number"""

    logger.info("=" * 60)
    logger.info(f"Importing ticket: {ticket_number}")
    logger.info("=" * 60)

    try:
        # Initialize database
        SessionMaker = init_database()
        session = SessionMaker()

        # Get ticket from API
        ticketing_client = TicketingAPIClient()
        logger.info("Fetching ticket from API...")
        tickets = ticketing_client.get_ticket_by_ticket_number(ticket_number)

        if not tickets or len(tickets) == 0:
            logger.error(f"Ticket {ticket_number} not found in ticketing system")
            return False

        ticket_data = tickets[0]
        logger.info("Ticket fetched successfully",
                   order_number=ticket_data.get('amazonOrderNumber'),
                   customer=ticket_data.get('customer', {}).get('name'))

        # Get entrance email
        ticket_details = ticket_data.get('ticketDetails', [])
        entrance_email = None

        for detail in ticket_details:
            if detail.get('entranceEmailBody'):
                entrance_email = {
                    'id': 'manual_import',
                    'subject': detail.get('entranceEmailSubject', ''),
                    'body': detail.get('entranceEmailBody', ''),
                    'from': detail.get('entranceEmailSenderAddress', ''),
                    'to': '',
                    'date': detail.get('createdDateTime', ''),
                    'snippet': detail.get('entranceEmailSubject', '')[:100]
                }
                break

        if not entrance_email:
            logger.warning("No entrance email found, will process without it")
            entrance_email = {
                'id': 'manual_import',
                'subject': f"Ticket {ticket_number}",
                'body': "No entrance email found",
                'from': ticket_data.get('customer', {}).get('emailAdress', ''),
                'to': '',
                'date': '',
                'snippet': ''
            }

        # Initialize orchestrator
        orchestrator = SupportAgentOrchestrator()

        # Process the ticket
        logger.info("Processing ticket with AI...")
        success = orchestrator._process_single_email(entrance_email)

        if success:
            logger.info("✓ Ticket imported and processed successfully!")
            return True
        else:
            logger.error("✗ Failed to process ticket")
            return False

    except Exception as e:
        logger.error("Error importing ticket", error=str(e), exc_info=True)
        return False
    finally:
        session.close()

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 import_single_ticket.py <ticket_number>")
        print("Example: python3 import_single_ticket.py DE25007154")
        sys.exit(1)

    ticket_number = sys.argv[1]
    success = import_ticket(ticket_number)
    sys.exit(0 if success else 1)
