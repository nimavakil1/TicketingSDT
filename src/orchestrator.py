"""
Main Orchestrator
Coordinates email monitoring, ticket processing, AI analysis, and action dispatch
"""
from typing import Dict, Any, Optional
from datetime import datetime
import time
import structlog

from config.settings import settings
from src.email.gmail_monitor import GmailMonitor
from src.api.ticketing_client import TicketingAPIClient, TicketingAPIError
from src.ai.ai_engine import AIEngine
from src.dispatcher.action_dispatcher import ActionDispatcher
from src.utils.supplier_manager import SupplierManager
from src.database.models import (
    ProcessedEmail,
    TicketState,
    Supplier,
    init_database
)

logger = structlog.get_logger(__name__)


class SupportAgentOrchestrator:
    """
    Main orchestrator for the AI support agent
    Handles the full workflow from email to action
    """

    def __init__(self):
        logger.info("Initializing AI Support Agent Orchestrator")

        # Initialize database
        self.SessionMaker = init_database()

        # Initialize components
        self.gmail_monitor = GmailMonitor()
        self.ticketing_client = TicketingAPIClient()
        self.ai_engine = AIEngine()

        logger.info(
            "Orchestrator initialized",
            phase=settings.deployment_phase,
            ai_provider=settings.ai_provider
        )

    def process_new_emails(self) -> int:
        """
        Process all new unprocessed emails

        Returns:
            Number of emails processed
        """
        logger.info("Checking for new emails")

        try:
            # Get unprocessed messages
            messages = self.gmail_monitor.get_unprocessed_messages()

            if not messages:
                logger.debug("No new messages to process")
                return 0

            logger.info("Processing new emails", count=len(messages))

            processed_count = 0
            for message in messages:
                try:
                    if self._process_single_email(message):
                        processed_count += 1
                except Exception as e:
                    logger.error(
                        "Failed to process email",
                        message_id=message.get('id'),
                        error=str(e)
                    )
                    # Continue processing other emails

            logger.info("Email processing complete", processed=processed_count, total=len(messages))
            return processed_count

        except Exception as e:
            logger.error("Error during email processing", error=str(e))
            return 0

    def _process_single_email(self, email_data: Dict[str, Any]) -> bool:
        """
        Process a single email through the full workflow

        Args:
            email_data: Email message data from Gmail

        Returns:
            True if successfully processed
        """
        gmail_message_id = email_data['id']
        subject = email_data.get('subject', '')
        from_address = email_data.get('from', '')

        logger.info(
            "Processing email",
            gmail_id=gmail_message_id,
            subject=subject[:100],
            from_addr=from_address
        )

        # Create database session
        session = self.SessionMaker()

        try:
            # Check if already processed (idempotency)
            existing = session.query(ProcessedEmail).filter_by(
                gmail_message_id=gmail_message_id
            ).first()

            if existing:
                logger.info("Email already processed, skipping", gmail_id=gmail_message_id)
                return False

            # Optional preparation mode: label only, skip AI + ticketing
            if getattr(settings, 'preparation_mode', False):
                self._mark_email_processed(session, email_data, None, None)
                self.gmail_monitor.mark_as_processed(gmail_message_id)
                session.commit()
                logger.info(
                    "Preparation mode: labeled message only",
                    gmail_id=gmail_message_id,
                    subject=subject[:100]
                )
                return True

            # Extract order number from email
            order_number = self._extract_order_number(email_data)

            if not order_number:
                logger.warning(
                    "Could not extract order number from email",
                    gmail_id=gmail_message_id,
                    subject=subject
                )
                # Mark as processed to avoid reprocessing
                self._mark_email_processed(session, email_data, None, None)
                self.gmail_monitor.mark_as_processed(gmail_message_id)
                return False

            logger.info("Extracted order number", order_number=order_number)

            # Get or create ticket
            ticket_data, ticket_state = self._get_or_create_ticket(
                session=session,
                email_data=email_data,
                order_number=order_number
            )

            if not ticket_data or not ticket_state:
                logger.error("Failed to get or create ticket", order_number=order_number)
                return False

            ticket_id = ticket_data.get('ticketNumber')
            logger.info("Processing ticket", ticket_number=ticket_id)

            # Build ticket history for AI context
            ticket_history = self._build_ticket_history(ticket_data)

            # AI analysis
            analysis = self.ai_engine.analyze_email(
                email_data=email_data,
                ticket_data=ticket_data,
                ticket_history=ticket_history
            )

            logger.info(
                "AI analysis complete",
                intent=analysis.get('intent'),
                confidence=analysis.get('confidence'),
                escalation=analysis.get('requires_escalation')
            )

            # Update ticket state
            self._update_ticket_state(session, ticket_state, analysis)

            # Dispatch action
            dispatcher = ActionDispatcher(self.ticketing_client)
            action_result = dispatcher.dispatch(
                analysis=analysis,
                ticket_id=ticket_state.ticket_id,
                ticket_number=ticket_state.ticket_number,
                ticket_status_id=ticket_state.ticket_status_id,
                owner_id=ticket_state.owner_id,
                db_session=session,
                gmail_message_id=gmail_message_id
            )

            logger.info("Action dispatched", result=action_result.get('action'))

            # Handle supplier communication if needed
            if analysis.get('supplier_action') and settings.deployment_phase >= 2:
                self._handle_supplier_communication(
                    session=session,
                    ticket_state=ticket_state,
                    ticket_data=ticket_data,
                    supplier_action=analysis['supplier_action']
                )

            # Mark email as processed
            self._mark_email_processed(
                session=session,
                email_data=email_data,
                ticket_state=ticket_state,
                order_number=order_number
            )

            # Mark in Gmail
            self.gmail_monitor.mark_as_processed(gmail_message_id)

            session.commit()
            logger.info("Email processing successful", gmail_id=gmail_message_id)

            return True

        except Exception as e:
            logger.error("Error processing email", error=str(e), gmail_id=gmail_message_id)
            session.rollback()
            return False

        finally:
            session.close()

    def _extract_order_number(self, email_data: Dict[str, Any]) -> Optional[str]:
        """Extract order number from email"""
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')

        # Try subject first
        order_number = self.gmail_monitor.extract_order_number(subject)
        if order_number:
            return order_number

        # Try body
        order_number = self.gmail_monitor.extract_order_number(body)
        return order_number

    def _get_or_create_ticket(
        self,
        session: Any,
        email_data: Dict[str, Any],
        order_number: str
    ) -> tuple[Optional[Dict], Optional[TicketState]]:
        """
        Get existing ticket or create new one

        Returns:
            Tuple of (ticket_data from API, ticket_state from DB)
        """
        try:
            # Try to get existing ticket from API
            tickets = self.ticketing_client.get_ticket_by_amazon_order_number(order_number)

            if tickets and len(tickets) > 0:
                ticket_data = tickets[0]
                ticket_number = ticket_data.get('ticketNumber')

                # Get or create ticket state in DB
                ticket_state = session.query(TicketState).filter_by(
                    ticket_number=ticket_number
                ).first()

                if not ticket_state:
                    ticket_state = self._create_ticket_state(session, ticket_data, order_number)

                return ticket_data, ticket_state

            else:
                # No existing ticket, create new one via API
                logger.info("Creating new ticket", order_number=order_number)

                sender_name, sender_email = self.gmail_monitor.parse_sender_info(
                    email_data.get('from', '')
                )

                # Classify ticket type (default to general inquiry)
                ticket_type_id = 6  # SupportEnquiry

                result = self.ticketing_client.upsert_ticket(
                    sales_order_reference=order_number,
                    ticket_type_id=ticket_type_id,
                    contact_name=sender_name,
                    entrance_email_body=email_data.get('body', ''),
                    entrance_email_date=email_data.get('date'),
                    entrance_email_subject=email_data.get('subject', ''),
                    entrance_email_sender_address=sender_email,
                    entrance_gmail_thread_id=email_data.get('thread_id')
                )

                if not result.get('succeeded'):
                    logger.error("Failed to create ticket", api_messages=result.get('messages', []))
                    return None, None

                # Fetch the newly created ticket
                tickets = self.ticketing_client.get_ticket_by_amazon_order_number(order_number)
                if tickets and len(tickets) > 0:
                    ticket_data = tickets[0]
                    ticket_state = self._create_ticket_state(session, ticket_data, order_number)
                    return ticket_data, ticket_state

                return None, None

        except TicketingAPIError as e:
            logger.error("Ticketing API error", error=str(e))
            return None, None

    def _create_ticket_state(
        self,
        session: Any,
        ticket_data: Dict[str, Any],
        order_number: str
    ) -> TicketState:
        """Create new ticket state in database"""
        sales_order = ticket_data.get('salesOrder', {})

        ticket_state = TicketState(
            ticket_number=ticket_data.get('ticketNumber'),
            ticket_id=ticket_data.get('ticketNumber'),  # Assuming ticket number is the ID
            order_number=order_number,
            customer_name=ticket_data.get('contactName'),
            customer_email=sales_order.get('customerEmail', ''),
            customer_language=ticket_data.get('customerLanguageCultureName', 'en-US'),
            supplier_name=sales_order.get('purchaseOrders', [{}])[0].get('supplierName', '') if sales_order.get('purchaseOrders') else '',
            ticket_type_id=ticket_data.get('ticketTypeId', 0),
            ticket_status_id=ticket_data.get('ticketStatusId', 1),
            owner_id=ticket_data.get('ownerId', settings.default_owner_id),
            current_state='new',
            last_action='created',
            last_action_date=datetime.utcnow()
        )

        session.add(ticket_state)
        session.commit()

        logger.info("Created ticket state", ticket_number=ticket_state.ticket_number)

        return ticket_state

    def _build_ticket_history(self, ticket_data: Dict[str, Any]) -> str:
        """Build a summary of ticket history for AI context"""
        history_parts = []

        ticket_details = ticket_data.get('ticketDetails', [])
        for detail in ticket_details[-5:]:  # Last 5 messages
            comment = detail.get('comment', '')
            sender = detail.get('receiverEmailAddress', 'Internal')
            if comment:
                history_parts.append(f"[{sender}]: {comment[:200]}")

        return "\n".join(history_parts) if history_parts else "No previous history"

    def _update_ticket_state(
        self,
        session: Any,
        ticket_state: TicketState,
        analysis: Dict[str, Any]
    ) -> None:
        """Update ticket state based on AI analysis"""
        ticket_state.customer_language = analysis.get('language', ticket_state.customer_language)
        ticket_state.ticket_type_id = analysis.get('ticket_type_id', ticket_state.ticket_type_id)
        ticket_state.last_action = analysis.get('intent', 'analyzed')
        ticket_state.last_action_date = datetime.utcnow()
        ticket_state.conversation_summary = analysis.get('summary', '')

        session.commit()

    def _handle_supplier_communication(
        self,
        session: Any,
        ticket_state: TicketState,
        ticket_data: Dict[str, Any],
        supplier_action: Dict[str, Any]
    ) -> None:
        """Handle supplier communication and tracking"""
        if not ticket_state.supplier_name:
            logger.warning("No supplier name available", ticket_number=ticket_state.ticket_number)
            return

        # Get supplier email from ticket data
        sales_order = ticket_data.get('salesOrder', {})
        purchase_orders = sales_order.get('purchaseOrders', [])

        if not purchase_orders:
            logger.warning("No purchase orders found", ticket_number=ticket_state.ticket_number)
            return

        supplier_email = "supplier@example.com"  # Default, should be in ticket data

        # Get or create supplier
        supplier_manager = SupplierManager(self.ticketing_client, session)
        supplier = supplier_manager.get_or_create_supplier(
            supplier_name=ticket_state.supplier_name,
            default_email=supplier_email
        )

        # Record supplier message
        supplier_manager.record_supplier_message(
            ticket_state=ticket_state,
            supplier=supplier,
            message_content=supplier_action.get('message', ''),
            purpose=supplier_action.get('action', 'general')
        )

    def _mark_email_processed(
        self,
        session: Any,
        email_data: Dict[str, Any],
        ticket_state: Optional[TicketState],
        order_number: Optional[str]
    ) -> None:
        """Mark email as processed in database"""
        processed_email = ProcessedEmail(
            gmail_message_id=email_data['id'],
            gmail_thread_id=email_data.get('thread_id'),
            ticket_id=ticket_state.id if ticket_state else None,
            order_number=order_number,
            subject=email_data.get('subject', ''),
            from_address=email_data.get('from', '')
        )

        session.add(processed_email)
        session.commit()

    def check_supplier_reminders(self) -> int:
        """
        Check for overdue supplier messages and send reminders

        Returns:
            Number of reminders sent
        """
        logger.info("Checking supplier reminders")

        session = self.SessionMaker()

        try:
            supplier_manager = SupplierManager(self.ticketing_client, session)
            reminders_sent = supplier_manager.check_and_send_reminders()

            session.commit()
            return reminders_sent

        except Exception as e:
            logger.error("Error checking supplier reminders", error=str(e))
            session.rollback()
            return 0

        finally:
            session.close()

    def run_forever(self) -> None:
        """
        Run the agent continuously with polling
        """
        logger.info(
            "Starting AI Support Agent",
            phase=settings.deployment_phase,
            poll_interval=settings.email_poll_interval_seconds
        )

        while True:
            try:
                # Process new emails
                self.process_new_emails()

                # Check supplier reminders (every cycle)
                self.check_supplier_reminders()

                # Wait before next poll
                time.sleep(settings.email_poll_interval_seconds)

            except KeyboardInterrupt:
                logger.info("Shutting down AI Support Agent")
                break

            except Exception as e:
                logger.error("Unexpected error in main loop", error=str(e))
                # Continue running despite errors
                time.sleep(settings.email_poll_interval_seconds)
