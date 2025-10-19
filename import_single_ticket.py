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

# Configure logging with more verbose output
import logging
logging.basicConfig(level=logging.DEBUG)

structlog.configure(
    processors=[
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    cache_logger_on_first_use=True,
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

        # Generate unique ID for this import
        import uuid
        unique_id = f"manual_import_{ticket_number}_{uuid.uuid4().hex[:8]}"

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
                subject = detail.get('entranceEmailSubject', '') or f"Ticket {ticket_number}"
                entrance_email = {
                    'id': unique_id,
                    'subject': subject,
                    'body': detail.get('entranceEmailBody', ''),
                    'from': detail.get('entranceEmailSenderAddress', ''),
                    'to': '',
                    'date': detail.get('createdDateTime', ''),
                    'snippet': subject[:100]
                }
                break

        if not entrance_email:
            logger.warning("No entrance email found, will process without it")
            entrance_email = {
                'id': unique_id,
                'subject': f"Ticket {ticket_number}",
                'body': "No entrance email found",
                'from': ticket_data.get('customer', {}).get('emailAdress', ''),
                'to': '',
                'date': '',
                'snippet': ''
            }

        # Create or get ticket state directly from ticket_data
        from src.database.models import TicketState

        logger.info("Creating/updating ticket state in database...")
        ticket_state = session.query(TicketState).filter_by(ticket_number=ticket_number).first()

        if not ticket_state:
            # Initialize orchestrator to use its _create_ticket_state method
            orchestrator = SupportAgentOrchestrator()
            order_number = ticket_data.get('amazonOrderNumber')
            ticket_state = orchestrator._create_ticket_state(session, ticket_data, order_number)
            session.add(ticket_state)
            session.commit()
            logger.info("Created new ticket state", ticket_number=ticket_number)
        else:
            logger.info("Ticket state already exists", ticket_number=ticket_number)

        # Now process with AI - build ticket history and analyze
        logger.info("Processing ticket with AI...")
        orchestrator = SupportAgentOrchestrator()
        ticket_history = orchestrator._build_ticket_history(ticket_data)

        # Get supplier language if available
        from src.database.models import Supplier
        supplier_name = ticket_data.get('salesOrder', {}).get('purchaseOrders', [{}])[0].get('supplierName', '')
        supplier_language = 'de-DE'  # Default
        if supplier_name:
            supplier = session.query(Supplier).filter(Supplier.name == supplier_name).first()
            if supplier and supplier.language_code:
                supplier_language = supplier.language_code

        # Call AI analysis
        from src.ai.ai_engine import AIEngine
        ai_engine = AIEngine()

        analysis = ai_engine.analyze_email(
            email_data=entrance_email,
            ticket_history=ticket_history,
            target_language=supplier_language
        )

        if analysis:
            logger.info("AI analysis complete",
                       action=analysis.get('action'),
                       confidence=analysis.get('confidence'))

            # Dispatch actions
            from src.dispatcher.action_dispatcher import ActionDispatcher
            dispatcher = ActionDispatcher()
            success = dispatcher.dispatch(analysis, ticket_state, session)

            session.commit()

            if success:
                logger.info("✓ Ticket imported and processed successfully!")
                return True
            else:
                logger.error("✗ Failed to dispatch actions")
                return False
        else:
            logger.error("✗ AI analysis returned None")
            return False

    except Exception as e:
        logger.error("Error importing ticket", error=str(e), exc_info=True)
        import traceback
        traceback.print_exc()
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
