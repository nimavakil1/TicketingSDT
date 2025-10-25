"""
Main Orchestrator
Coordinates email monitoring, ticket processing, AI analysis, and action dispatch
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import time
import structlog

from config.settings import settings
from src.email.gmail_monitor import GmailMonitor
from src.api.ticketing_client import TicketingAPIClient, TicketingAPIError
from src.ai.ai_engine import AIEngine
from src.dispatcher.action_dispatcher import ActionDispatcher
from src.utils.supplier_manager import SupplierManager
from src.utils.text_filter import TextFilter
from src.utils.error_alerting import ErrorAlerting
from src.database.models import (
    ProcessedEmail,
    TicketState,
    Supplier,
    PendingEmailRetry,
    AIDecisionLog,
    Attachment,
    init_database
)
from src.utils.message_service import MessageService
from src.utils.message_formatter import MessageFormatter
from src.utils.audit_logger import log_ticket_created

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
        self.session = self.SessionMaker()  # Main session for settings checks

        # Initialize components
        self.gmail_monitor = GmailMonitor()
        self.ticketing_client = TicketingAPIClient()
        self.ai_engine = AIEngine()

        # Initialize error alerting if configured
        self.error_alerting = None
        if settings.error_alerts_enabled and settings.error_alert_email:
            try:
                from src.email.gmail_sender import GmailSender
                gmail_sender = GmailSender()
                self.error_alerting = ErrorAlerting(
                    alert_email=settings.error_alert_email,
                    gmail_sender=gmail_sender,
                    rate_limit_minutes=settings.error_alert_rate_limit_minutes
                )
                logger.info("Error alerting enabled", alert_email=settings.error_alert_email)
            except Exception as e:
                logger.warning("Failed to initialize error alerting", error=str(e))
        else:
            logger.info("Error alerting disabled")

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
        # Check if Gmail monitoring is paused
        try:
            from sqlalchemy import text
            result = self.session.execute(
                text("SELECT value FROM system_settings WHERE key = 'gmail_monitoring_paused'")
            ).fetchone()

            if result and result[0] == 'true':
                logger.debug("Gmail monitoring is paused - skipping email check")
                return 0
        except Exception as e:
            # If settings table doesn't exist yet, continue normally
            logger.debug(f"Could not check pause setting: {e}")

        logger.info("Checking for new emails")

        try:
            # Get unprocessed messages with configured lookback window
            messages = self.gmail_monitor.get_unprocessed_messages(
                lookback_minutes=settings.gmail_lookback_minutes
            )

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
        subject = email_data.get('subject') or ''
        body = email_data.get('body', '')
        from_address = email_data.get('from', '')

        # Skip emails with no subject (bounce messages, system notifications)
        if not subject:
            logger.info(
                "Skipping email with no subject",
                gmail_id=gmail_message_id,
                from_addr=from_address
            )
            # Mark as successfully processed (intentional skip) so we don't keep trying
            session = self.SessionMaker()
            try:
                self._mark_email_processed(session, email_data, None, None, success=True)
                self.gmail_monitor.mark_as_processed(gmail_message_id)
                session.commit()
            except Exception as e:
                logger.error("Failed to mark empty subject email as processed", error=str(e))
                session.rollback()
            finally:
                session.close()
            return False

        logger.info(
            "Processing email",
            gmail_id=gmail_message_id,
            subject=subject[:100],
            from_addr=from_address
        )

        # Create database session
        session = self.SessionMaker()

        # Initialize text filter
        text_filter = TextFilter(session)

        # Check if email should be ignored (auto-replies, OOO, etc.)
        should_ignore, ignore_reason = text_filter.should_ignore_email(subject, body)
        if should_ignore:
            logger.info(
                "Ignoring email based on pattern match",
                gmail_id=gmail_message_id,
                reason=ignore_reason,
                subject=subject[:100]
            )
            # Mark as successfully processed (intentional skip)
            try:
                self._mark_email_processed(
                    session, email_data, None, None,
                    success=True,
                    error_message=f"Ignored: {ignore_reason}"
                )
                self.gmail_monitor.mark_as_processed(gmail_message_id)
                session.commit()
            except Exception as e:
                logger.error("Failed to mark ignored email as processed", error=str(e))
                session.rollback()
            finally:
                session.close()
            return False

        # Filter email body to remove skip text blocks
        original_body = body
        filtered_body = text_filter.filter_email_body(body)
        if filtered_body != original_body:
            logger.info(
                "Email body filtered",
                gmail_id=gmail_message_id,
                original_length=len(original_body),
                filtered_length=len(filtered_body),
                saved_chars=len(original_body) - len(filtered_body)
            )
            # Update email_data with filtered body for AI analysis
            email_data = {**email_data, 'body': filtered_body}

        try:
            # Check if already successfully processed (idempotency)
            existing = session.query(ProcessedEmail).filter_by(
                gmail_message_id=gmail_message_id
            ).first()

            if existing and existing.success:
                logger.debug("Email already successfully processed, skipping", gmail_id=gmail_message_id)
                return False

            # If existing but not successful, we'll retry (don't return here)

            # NEW WORKFLOW: Extract all identifiers and resolve ticket
            subject_text = email_data.get('subject') or ''
            body_text = email_data.get('body', '')
            identifiers = self.gmail_monitor.extract_identifiers(subject_text, body_text)

            logger.info(
                "Extracted identifiers from email",
                gmail_id=gmail_message_id,
                ticket_number=identifiers.get('ticket_number'),
                order_number=identifiers.get('order_number'),
                purchase_order_number=identifiers.get('purchase_order_number')
            )

            # Resolve ticket using new workflow
            ticket_data, ticket_state = self._resolve_ticket_with_new_workflow(
                session=session,
                email_data=email_data,
                identifiers=identifiers
            )

            # If no identifiers found, create ticket anyway and mark for escalation
            if not ticket_data and not ticket_state and not any(identifiers.values()):
                logger.warning(
                    "No identifiers found, creating ticket and marking for escalation",
                    gmail_id=gmail_message_id,
                    subject=subject[:100]
                )
                # Create ticket without order number
                order_num = None
                ticket_number = self._create_ticket_in_old_system(email_data, order_num)

                if ticket_number:
                    # Fetch the newly created ticket by ID
                    try:
                        ticket_data = self.ticketing_client.get_ticket_by_id(ticket_number)
                        if ticket_data:
                            ticket_state = self._create_ticket_state(session, ticket_data, order_num)
                            # Mark for escalation
                            ticket_state.escalated = True
                            ticket_state.escalation_reason = "No identifiers found in email (no order number, ticket number, or PO)"
                            ticket_state.escalation_date = datetime.utcnow()
                            session.commit()
                            logger.info(
                                "Created ticket and marked for escalation",
                                ticket_number=ticket_state.ticket_number
                            )
                    except Exception as e:
                        logger.error("Failed to fetch escalated ticket", ticket_id=ticket_number, error=str(e))

            # If still no ticket after all attempts, schedule retry
            if not ticket_data or not ticket_state:
                logger.warning(
                    "Could not resolve or create ticket; scheduling retry",
                    gmail_id=gmail_message_id,
                    identifiers=identifiers
                )
                self._schedule_retry(session, email_data, reason="ticket_resolution_failed")
                self._mark_email_processed(
                    session, email_data, None, identifiers.get('order_number'),
                    success=False,
                    error_message="Could not resolve or create ticket"
                )
                # Don't mark in Gmail - allow retry
                return False

            ticket_id = ticket_data.get('ticketNumber')
            logger.info("Processing ticket", ticket_number=ticket_id)

            # Build ticket history for AI context
            ticket_history = self._build_ticket_history(ticket_data)

            # AI analysis (respect supplier language for supplier actions)
            supplier_language = self._resolve_supplier_language(ticket_data)
            analysis = self.ai_engine.analyze_email(
                email_data=email_data,
                ticket_data=ticket_data,
                ticket_history=ticket_history,
                supplier_language=supplier_language
            )

            logger.info(
                "AI analysis complete",
                intent=analysis.get('intent'),
                confidence=analysis.get('confidence'),
                escalation=analysis.get('requires_escalation')
            )

            # Update ticket state
            self._update_ticket_state(session, ticket_state, analysis)

            # Extract and update PO number and supplier references
            self._update_ticket_identifiers(session, ticket_state, ticket_data, analysis)

            # Create pending messages for Phase 1 approval (human review required)
            ai_decision_id = self._log_ai_decision(session, ticket_state, analysis, gmail_message_id)
            self._create_pending_messages_from_analysis(
                session, ticket_state, ticket_data, analysis, ai_decision_id
            )

            # Get raw owner_id from API (may be None)
            raw_api_owner_id = ticket_data.get('ownerId')

            # Pass the raw owner_id (even if None) to dispatcher
            # According to API docs: "pass the same ownerId that you receive, leave it empty if no owner"
            logger.info(
                "Dispatching with owner_id from API",
                ticket_id=ticket_state.ticket_id,
                raw_owner_id=raw_api_owner_id,
                raw_owner_id_type=type(raw_api_owner_id).__name__
            )

            # Dispatch action
            dispatcher = ActionDispatcher(self.ticketing_client)
            action_result = dispatcher.dispatch(
                analysis=analysis,
                ticket_id=ticket_state.ticket_id,
                ticket_number=ticket_state.ticket_number,
                owner_id=raw_api_owner_id  # Pass raw value from API, not database fallback
            )

            logger.info("Action dispatched", result=action_result.get('action'))

            # Handle supplier communication if needed (Phase 2+ only)
            if analysis.get('supplier_action') and settings.deployment_phase >= 2:
                self._handle_supplier_communication(
                    session=session,
                    ticket_state=ticket_state,
                    ticket_data=ticket_data,
                    supplier_action=analysis['supplier_action']
                )

            # Mark email as successfully processed in database
            self._mark_email_processed(
                session=session,
                email_data=email_data,
                ticket_state=ticket_state,
                order_number=identifiers.get('order_number'),
                success=True
            )

            session.commit()
            logger.info("Email processing successful", gmail_id=gmail_message_id)

            # Only mark in Gmail after successful database commit
            self.gmail_monitor.mark_as_processed(gmail_message_id)

            return True

        except Exception as e:
            logger.error("Error processing email", error=str(e), gmail_id=gmail_message_id)
            try:
                session.rollback()
                # Schedule a retry and mark as failed (will retry later)
                self._schedule_retry(session, email_data, reason=f"exception:{type(e).__name__}")
                self._mark_email_processed(
                    session, email_data, None, None,
                    success=False,
                    error_message=f"Exception: {type(e).__name__}: {str(e)}"
                )
                session.commit()
                # Don't mark in Gmail - allow retry
            except Exception as ie:
                logger.error("Failed to record retry after exception", error=str(ie))
            return False

        finally:
            session.close()

    def _extract_order_number(self, email_data: Dict[str, Any]) -> Optional[str]:
        """Extract order number from email"""
        subject = email_data.get('subject') or ''
        body = email_data.get('body', '')

        # Try subject first
        order_number = self.gmail_monitor.extract_order_number(subject)
        if order_number:
            return order_number

        # Try body
        order_number = self.gmail_monitor.extract_order_number(body)
        return order_number

    def _schedule_retry(self, session: Any, email_data: Dict[str, Any], reason: str) -> None:
        """Schedule a retry for an email that couldn't be linked to a ticket."""
        if not settings.retry_enabled:
            return
        gmail_id = email_data.get('id')
        existing = session.query(PendingEmailRetry).filter_by(gmail_message_id=gmail_id).first()
        next_at = datetime.utcnow() + timedelta(minutes=settings.retry_delay_minutes)
        if existing:
            existing.next_attempt_at = next_at
            existing.last_error = reason
        else:
            retry = PendingEmailRetry(
                gmail_message_id=gmail_id,
                gmail_thread_id=email_data.get('thread_id'),
                subject=email_data.get('subject') or '',
                from_address=email_data.get('from', ''),
                attempts=0,
                next_attempt_at=next_at,
                last_error=reason
            )
            session.add(retry)
        session.commit()
        logger.info("Scheduled retry", gmail_id=gmail_id, reason=reason, next_attempt_at=str(next_at))

    def process_pending_retries(self) -> int:
        """Process pending email retries that are due."""
        if not settings.retry_enabled:
            return 0
        session = self.SessionMaker()
        processed = 0
        try:
            due = session.query(PendingEmailRetry).filter(
                PendingEmailRetry.next_attempt_at <= datetime.utcnow(),
                PendingEmailRetry.attempts < settings.retry_max_attempts
            ).all()
            for item in due:
                try:
                    # Fetch email details fresh from Gmail
                    email_data = self.gmail_monitor._get_message_details(item.gmail_message_id)
                    if not email_data:
                        item.attempts += 1
                        item.next_attempt_at = datetime.utcnow() + timedelta(minutes=settings.retry_delay_minutes)
                        item.last_error = 'gmail_fetch_failed'
                        session.commit()
                        continue

                    # Try Amazon order lookup (base + variants)
                    order_number = self._extract_order_number(email_data)
                    ticket_data = None
                    ticket_state = None
                    if order_number:
                        tickets = self.ticketing_client.get_ticket_by_amazon_order_number(order_number) or []
                        if not tickets:
                            for ref in (f"{order_number}-1", f"{order_number}_1"):
                                t = self.ticketing_client.get_ticket_by_amazon_order_number(ref)
                                if t:
                                    tickets = t
                                    break
                        if tickets:
                            ticket_data = tickets[0]
                            ticket_state = session.query(TicketState).filter_by(ticket_number=ticket_data.get('ticketNumber')).first()
                            if not ticket_state:
                                ticket_state = self._create_ticket_state(session, ticket_data, order_number)

                    # Fallback: ticket number / PO number
                    if not ticket_data:
                        t = self._find_ticket_by_ticket_or_po(email_data)
                        if t:
                            ticket_data = t
                            ticket_state = session.query(TicketState).filter_by(ticket_number=ticket_data.get('ticketNumber')).first()
                            if not ticket_state:
                                ticket_state = self._create_ticket_state(session, ticket_data, order_number=None)

                    if ticket_data and ticket_state:
                        # Proceed with normal analysis and Phase 1 internal note
                        ticket_history = self._build_ticket_history(ticket_data)
                        supplier_language = self._resolve_supplier_language(ticket_data)
                        analysis = self.ai_engine.analyze_email(
                            email_data=email_data,
                            ticket_data=ticket_data,
                            ticket_history=ticket_history,
                            supplier_language=supplier_language
                        )
                        dispatcher = ActionDispatcher(self.ticketing_client)
                        dispatcher.dispatch(
                            analysis=analysis,
                            ticket_id=ticket_state.ticket_id,
                            ticket_number=ticket_state.ticket_number,
                            owner_id=ticket_state.owner_id
                        )
                        session.delete(item)
                        session.commit()
                        processed += 1
                    else:
                        # Not yet available; reschedule or drop after max attempts
                        item.attempts += 1
                        if item.attempts >= settings.retry_max_attempts:
                            item.last_error = 'max_attempts_reached'
                        item.next_attempt_at = datetime.utcnow() + timedelta(minutes=settings.retry_delay_minutes)
                        session.commit()
                except Exception as e:
                    logger.error("Failed processing pending retry", gmail_id=item.gmail_message_id, error=str(e))
                    item.attempts += 1
                    item.next_attempt_at = datetime.utcnow() + timedelta(minutes=settings.retry_delay_minutes)
                    item.last_error = str(e)
                    session.commit()
            return processed
        finally:
            session.close()

    def _find_existing_ticket_in_db(
        self,
        session: Any,
        identifiers: Dict[str, Optional[str]]
    ) -> Optional[TicketState]:
        """
        Check if we already have a ticket for these identifiers in our database.
        Priority: ticket_number > order_number > purchase_order_number

        Args:
            session: Database session
            identifiers: Dict with ticket_number, order_number, purchase_order_number

        Returns:
            TicketState if found, None otherwise
        """
        # Try ticket number first (highest priority)
        if identifiers.get('ticket_number'):
            ticket = session.query(TicketState).filter_by(
                ticket_number=identifiers['ticket_number']
            ).first()
            if ticket:
                logger.info(
                    "Found existing ticket in DB by ticket number",
                    ticket_number=identifiers['ticket_number']
                )
                return ticket

        # Try order number
        if identifiers.get('order_number'):
            ticket = session.query(TicketState).filter_by(
                order_number=identifiers['order_number']
            ).first()
            if ticket:
                logger.info(
                    "Found existing ticket in DB by order number",
                    order_number=identifiers['order_number'],
                    ticket_number=ticket.ticket_number
                )
                return ticket

        # Try purchase order number
        if identifiers.get('purchase_order_number'):
            ticket = session.query(TicketState).filter_by(
                purchase_order_number=identifiers['purchase_order_number']
            ).first()
            if ticket:
                logger.info(
                    "Found existing ticket in DB by PO number",
                    purchase_order_number=identifiers['purchase_order_number'],
                    ticket_number=ticket.ticket_number
                )
                return ticket

        return None

    def _find_existing_ticket_in_api(
        self,
        identifiers: Dict[str, Optional[str]]
    ) -> Optional[Dict[str, Any]]:
        """
        Check if ticket exists in old ticketing system.
        Priority: ticket_number > order_number > purchase_order_number

        Args:
            identifiers: Dict with ticket_number, order_number, purchase_order_number

        Returns:
            Ticket data from API if found, None otherwise
        """
        # Try ticket number first (highest priority)
        if identifiers.get('ticket_number'):
            try:
                tickets = self.ticketing_client.get_ticket_by_ticket_number(
                    identifiers['ticket_number']
                )
                if tickets:
                    logger.info(
                        "Found existing ticket in API by ticket number",
                        ticket_number=identifiers['ticket_number']
                    )
                    return self._select_latest_ticket(tickets)
            except TicketingAPIError as e:
                logger.warning(
                    "API error searching by ticket number",
                    error=str(e)
                )

        # Try order number
        if identifiers.get('order_number'):
            order_num = identifiers['order_number']
            try:
                tickets = self.ticketing_client.get_ticket_by_amazon_order_number(order_num)
                if tickets:
                    logger.info(
                        "Found existing ticket in API by order number",
                        order_number=order_num
                    )
                    return self._select_latest_ticket(tickets)
            except TicketingAPIError as e:
                logger.warning(
                    "API error searching by order number",
                    error=str(e)
                )

        # Try purchase order number
        if identifiers.get('purchase_order_number'):
            try:
                tickets = self.ticketing_client.get_ticket_by_purchase_order_number(
                    identifiers['purchase_order_number']
                )
                if tickets:
                    logger.info(
                        "Found existing ticket in API by PO number",
                        purchase_order_number=identifiers['purchase_order_number']
                    )
                    return self._select_latest_ticket(tickets)
            except TicketingAPIError as e:
                logger.warning(
                    "API error searching by PO number",
                    error=str(e)
                )

        return None

    def _create_ticket_in_old_system(
        self,
        email_data: Dict[str, Any],
        order_number: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a new ticket in the old ticketing system.
        The API returns the ticket number in the 'serviceResult' field.

        Args:
            email_data: Email data
            order_number: Amazon order number if available

        Returns:
            Ticket number if created successfully, None otherwise
        """
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        from_address = email_data.get('from', '')

        logger.info(
            "Creating new ticket in old system",
            order_number=order_number,
            subject=subject[:100]
        )

        try:
            # Create ticket via API
            result = self.ticketing_client.create_ticket(
                subject=subject,
                body=body,
                customer_email=from_address,
                order_number=order_number
            )

            # Extract ticket number from serviceResult
            ticket_number = result.get('serviceResult')

            logger.info(
                "Ticket created in old system",
                ticket_number=ticket_number,
                result=result
            )
            return ticket_number

        except TicketingAPIError as e:
            logger.error(
                "Failed to create ticket in old system",
                error=str(e),
                order_number=order_number
            )
            return None

    def _search_for_ticket_with_retries(
        self,
        identifiers: Dict[str, Optional[str]],
        max_retries: int = 4,
        retry_delays: list = [5, 10, 20, 120]
    ) -> Optional[Dict[str, Any]]:
        """
        Search for newly created ticket with exponential backoff.
        Old system may not index ticket immediately after creation.

        Args:
            identifiers: Dict with ticket_number, order_number, purchase_order_number
            max_retries: Maximum number of retry attempts
            retry_delays: Delay in seconds for each retry [5s, 10s, 20s, 120s]

        Returns:
            Ticket data if found, None otherwise
        """
        for attempt in range(max_retries):
            if attempt > 0:
                delay = retry_delays[attempt - 1] if attempt - 1 < len(retry_delays) else retry_delays[-1]
                logger.info(
                    "Waiting before retry",
                    attempt=attempt + 1,
                    delay_seconds=delay
                )
                time.sleep(delay)

            logger.info(
                "Searching for ticket",
                attempt=attempt + 1,
                max_retries=max_retries
            )

            ticket_data = self._find_existing_ticket_in_api(identifiers)
            if ticket_data:
                logger.info(
                    "Found ticket after retry",
                    attempt=attempt + 1,
                    ticket_number=ticket_data.get('ticketNumber')
                )
                return ticket_data

        logger.warning(
            "Ticket not found after all retries",
            max_retries=max_retries,
            identifiers=identifiers
        )
        return None

    def _resolve_ticket_with_new_workflow(
        self,
        session: Any,
        email_data: Dict[str, Any],
        identifiers: Dict[str, Optional[str]]
    ) -> tuple[Optional[Dict], Optional[TicketState]]:
        """
        Resolve ticket using new workflow:
        1. Check database for existing ticket
        2. If not in DB, check old system API
        3. If not in API, create ticket in old system
        4. Search for newly created ticket with retries
        5. Import ticket to our DB

        Args:
            session: Database session
            email_data: Email data
            identifiers: Dict with ticket_number, order_number, purchase_order_number

        Returns:
            Tuple of (ticket_data from API, ticket_state from DB)
        """
        # Step 1: Check our database first
        logger.info("Step 1: Checking database for existing ticket")
        ticket_state = self._find_existing_ticket_in_db(session, identifiers)

        if ticket_state:
            # Found in DB, get fresh data from API
            try:
                tickets = self.ticketing_client.get_ticket_by_ticket_number(
                    ticket_state.ticket_number
                )
                if tickets:
                    ticket_data = self._select_latest_ticket(tickets)
                    logger.info(
                        "Found ticket in DB, fetched fresh data from API",
                        ticket_number=ticket_state.ticket_number
                    )
                    return (ticket_data, ticket_state)
            except TicketingAPIError:
                pass

            # If API call failed, return what we have
            return (None, ticket_state)

        # Step 2: Not in DB, check old system API
        logger.info("Step 2: Checking old system API for existing ticket")
        ticket_data = self._find_existing_ticket_in_api(identifiers)

        if ticket_data:
            # Found in API, import to our DB
            logger.info(
                "Found ticket in API, importing to DB",
                ticket_number=ticket_data.get('ticketNumber')
            )
            # Get order number from identifiers or ticket data
            order_num = identifiers.get('order_number') or \
                       ticket_data.get('orderDetails', {}).get('orderNumber')

            ticket_state = self._create_ticket_state(session, ticket_data, order_num)
            return (ticket_data, ticket_state)

        # Step 3: Not in API, create new ticket
        # Need at least one identifier to proceed
        if not any(identifiers.values()):
            logger.warning(
                "No identifiers found, cannot create ticket",
                subject=email_data.get('subject', '')[:100]
            )
            return (None, None)

        logger.info("Step 3: Creating new ticket in old system")
        order_num = identifiers.get('order_number')
        ticket_number = self._create_ticket_in_old_system(email_data, order_num)

        if not ticket_number:
            logger.error("Failed to create ticket in old system")
            return (None, None)

        # Step 4: Fetch newly created ticket by ticket ID
        logger.info("Step 4: Fetching newly created ticket", ticket_id=ticket_number)

        try:
            ticket_data = self.ticketing_client.get_ticket_by_id(ticket_number)
            if not ticket_data:
                logger.error("Ticket not found by ID", ticket_id=ticket_number)
                return (None, None)
        except Exception as e:
            logger.error("Failed to fetch ticket", ticket_id=ticket_number, error=str(e))
            return (None, None)

        # Step 5: Import ticket to our DB
        logger.info(
            "Step 5: Importing newly created ticket to DB",
            ticket_number=ticket_data.get('ticketNumber')
        )
        ticket_state = self._create_ticket_state(session, ticket_data, order_num)

        return (ticket_data, ticket_state)

    def _find_ticket_by_ticket_or_po(self, email_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Try to locate an existing ticket by ticket number or purchase order number.

        Returns the ticket data dict if found, otherwise None.
        If multiple tickets are found, returns the one with the latest ticket number (by numeric part).
        """
        subject = email_data.get('subject') or ''
        body = email_data.get('body', '')

        # Try ticket number
        ticket_number = self.gmail_monitor.extract_ticket_number(subject) or \
                        self.gmail_monitor.extract_ticket_number(body)
        if ticket_number:
            try:
                tickets = self.ticketing_client.get_ticket_by_ticket_number(ticket_number)
                if tickets:
                    return self._select_latest_ticket(tickets)
            except TicketingAPIError:
                pass

        # Try purchase order number
        po_number = self.gmail_monitor.extract_purchase_order_number(subject) or \
                    self.gmail_monitor.extract_purchase_order_number(body)
        if po_number:
            try:
                tickets = self.ticketing_client.get_ticket_by_purchase_order_number(po_number)
                if tickets:
                    return self._select_latest_ticket(tickets)
            except TicketingAPIError:
                pass

        return None

    def _select_latest_ticket(self, tickets: list[dict]) -> dict:
        """Select the latest ticket by ticket number numeric part."""
        def ticket_sort_key(t: dict) -> int:
            tn = str(t.get('ticketNumber', ''))
            # Expect format like DE25006528; extract numeric part
            import re
            m = re.match(r'^[A-Z]{2}(\d+)$', tn)
            if m:
                try:
                    return int(m.group(1))
                except Exception:
                    return 0
            return 0

        try:
            return sorted(tickets, key=ticket_sort_key, reverse=True)[0]
        except Exception:
            return tickets[0]

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
            # Try to get existing ticket from API (base and variants)
            tickets = self.ticketing_client.get_ticket_by_amazon_order_number(order_number) or []
            if not tickets:
                for ref in (f"{order_number}-1", f"{order_number}_1"):
                    t = self.ticketing_client.get_ticket_by_amazon_order_number(ref)
                    if t:
                        tickets = t
                        break

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
                # No existing ticket
                if settings.deployment_phase >= 2:
                    logger.info("No ticket found; Phase >=2 may create new ticket", order_number=order_number)
                else:
                    logger.info("No ticket found; Phase 1 skips creation", order_number=order_number)
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

        # Log raw owner_id from API to understand what value we get
        raw_owner_id = ticket_data.get('ownerId')
        logger.info(
            "Raw owner_id from API",
            raw_owner_id=raw_owner_id,
            raw_owner_id_type=type(raw_owner_id).__name__,
            raw_owner_id_repr=repr(raw_owner_id),
            ticket_number=ticket_data.get('ticketNumber')
        )

        # Extract purchase order data
        purchase_orders = sales_order.get('purchaseOrders', [])
        po_number = None
        supplier_name = ''
        supplier_email = ''
        supplier_phone = ''

        if purchase_orders and len(purchase_orders) > 0:
            po_data = purchase_orders[0]
            po_number = po_data.get('purchaseOrderNumber')
            supplier_name = po_data.get('supplierName', '')
            supplier_email = po_data.get('supplierEmail', '')
            supplier_phone = po_data.get('supplierPhone', '')

        # Extract customer address
        customer_address = sales_order.get('customerAddress', '')
        customer_city = sales_order.get('customerCity', '')
        customer_postal_code = sales_order.get('customerPostalCode', '')
        customer_country = sales_order.get('customerCountry', '')
        customer_phone = sales_order.get('customerPhone', '')

        # Extract tracking information from purchaseOrders -> deliveries -> deliveryParcels
        purchase_orders = sales_order.get('purchaseOrders', [])
        tracking_number = ''
        tracking_url = ''
        carrier_name = ''

        found_tracking = False
        for purchase_order in purchase_orders:
            deliveries = purchase_order.get('deliveries', [])
            for delivery in deliveries:
                delivery_parcels = delivery.get('deliveryParcels', [])
                for parcel in delivery_parcels:
                    if parcel.get('traceUrl') and parcel.get('traceUrl').strip():
                        tracking_number = parcel.get('trackNumber', '')
                        tracking_url = parcel.get('traceUrl', '')
                        carrier_name = parcel.get('shipmentMethod', {}).get('name1', '')
                        logger.info(
                            "Found valid tracking during ticket creation",
                            ticket_number=ticket_data.get('ticketNumber'),
                            trackingNumber=tracking_number,
                            traceUrl=tracking_url,
                            carrierName=carrier_name
                        )
                        found_tracking = True
                        break
                if found_tracking:
                    break
            if found_tracking:
                break

        delivery_status = sales_order.get('deliveryStatus', '')
        expected_delivery_date = sales_order.get('expectedDeliveryDate', '')

        # Extract product details
        import json
        product_details = None
        sales_order_items = sales_order.get('salesOrderItems', [])
        if sales_order_items:
            products = []
            for item in sales_order_items:
                products.append({
                    'sku': item.get('sku', ''),
                    'title': item.get('productTitle', ''),
                    'quantity': item.get('quantity', 1),
                    'price': item.get('unitPrice', 0)
                })
            product_details = json.dumps(products)

        # Extract order financial details
        order_total = sales_order.get('totalAmount', 0)
        order_currency = sales_order.get('currency', 'EUR')
        order_date = sales_order.get('orderDate', '')

        ticket_state = TicketState(
            ticket_number=ticket_data.get('ticketNumber'),
            ticket_id=(
                ticket_data.get('id')
                or ticket_data.get('ticketId')
                or ticket_data.get('ticketID')
                or ticket_data.get('ticketNumber')
            ),
            order_number=order_number,
            purchase_order_number=po_number,
            customer_name=ticket_data.get('contactName'),
            customer_email=sales_order.get('customerEmail', ''),
            customer_language=ticket_data.get('customerLanguageCultureName', 'en-US'),
            customer_address=customer_address,
            customer_city=customer_city,
            customer_postal_code=customer_postal_code,
            customer_country=customer_country,
            customer_phone=customer_phone,
            supplier_name=supplier_name,
            supplier_email=supplier_email,
            supplier_phone=supplier_phone,
            tracking_number=tracking_number,
            tracking_url=tracking_url,
            carrier_name=carrier_name,
            delivery_status=delivery_status,
            expected_delivery_date=expected_delivery_date,
            product_details=product_details,
            order_total=order_total,
            order_currency=order_currency,
            order_date=order_date,
            ticket_type_id=ticket_data.get('ticketTypeId', 0),
            ticket_status_id=ticket_data.get('ticketStatusId', 1),
            owner_id=ticket_data.get('ownerId') or settings.default_owner_id,
            current_state='new',
            last_action='created',
            last_action_date=datetime.utcnow()
        )

        session.add(ticket_state)
        session.commit()

        # Log ticket creation
        log_ticket_created(
            db=session,
            ticket_number=ticket_state.ticket_number,
            created_by="System"
        )

        logger.info("Created ticket state", ticket_number=ticket_state.ticket_number)

        return ticket_state

    def _build_ticket_history(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build structured ticket history for AI context
        Returns a clean JSON structure instead of text blobs
        """
        import json

        customer_messages = []
        supplier_messages = []
        internal_notes = []

        ticket_details = ticket_data.get('ticketDetails', [])

        for detail in ticket_details:
            comment = detail.get('comment', '')
            created_at = detail.get('createdDateTime', '')
            source = detail.get('sourceTicketSideTypeId')
            target = detail.get('targetTicketSideTypeId')

            if not comment:
                continue

            # Skip ALL AI Agent messages (case-insensitive)
            comment_lower = comment.strip().lower()
            # Check for any AI Agent related message
            if (comment_lower.startswith('ai agent') or
                'ai agent proposes' in comment_lower or
                'ai agent suggests' in comment_lower or
                comment.strip().startswith('🚨')):  # Escalation emoji
                continue

            # Parse date to simpler format
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                timestamp = dt.strftime('%Y-%m-%d %H:%M')
            except:
                timestamp = created_at[:16] if len(created_at) >= 16 else created_at

            # Determine message type based on source and target
            # 1 = System/Operator, 2 = Customer, 3 = Supplier
            if source == 2 and target == 1:
                # Customer to us
                customer_messages.append({
                    'timestamp': timestamp,
                    'direction': 'inbound',
                    'message': comment[:400]  # Slightly longer for context
                })
            elif source == 1 and target == 2:
                # Us to customer
                customer_messages.append({
                    'timestamp': timestamp,
                    'direction': 'outbound',
                    'message': comment[:400]
                })
            elif source == 1 and target == 3:
                # Us to supplier
                supplier_messages.append({
                    'timestamp': timestamp,
                    'direction': 'outbound',
                    'message': comment[:400]
                })
            elif source == 3 and target == 1:
                # Supplier to us
                supplier_messages.append({
                    'timestamp': timestamp,
                    'direction': 'inbound',
                    'message': comment[:400]
                })
            elif source == 1 and target == 1:
                # Internal note
                internal_notes.append({
                    'timestamp': timestamp,
                    'note': comment[:250]
                })

        # Return structured data (keep last N messages for each thread)
        return {
            'customer_thread': customer_messages[-4:],  # Last 4 customer exchanges
            'supplier_thread': supplier_messages[-4:],  # Last 4 supplier exchanges
            'internal_notes': internal_notes[-3:]  # Last 3 internal notes
        }


    def _resolve_supplier_language(self, ticket_data: dict) -> str:
        """Determine supplier communication language using overrides or default."""
        try:
            sales_order = ticket_data.get('salesOrder', {}) if ticket_data else {}
            pos = sales_order.get('purchaseOrders') or []
            supplier_name = pos[0].get('supplierName', '') if pos else ''
        except Exception:
            supplier_name = ''

        overrides = getattr(settings, 'supplier_language_overrides', {}) or {}
        if supplier_name and supplier_name in overrides:
            return overrides[supplier_name]
        return getattr(settings, 'supplier_default_language', 'en-US')

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

        # Update conversation summaries from AI reasoning
        conversation_updates = analysis.get('conversation_updates', {})
        if conversation_updates:
            ticket_state.customer_conversation_summary = conversation_updates.get('customer_summary')
            ticket_state.supplier_conversation_summary = conversation_updates.get('supplier_summary')
            ticket_state.pending_customer_promises = conversation_updates.get('customer_promises')
            ticket_state.pending_supplier_requests = conversation_updates.get('supplier_requests')

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
        order_number: Optional[str],
        success: bool = True,
        error_message: Optional[str] = None
    ) -> None:
        """Mark email as processed in database"""
        gmail_id = email_data['id']

        # Check if email already exists in database
        existing = session.query(ProcessedEmail).filter_by(
            gmail_message_id=gmail_id
        ).first()

        if existing:
            # Update existing record
            existing.processed_at = datetime.utcnow()
            existing.ticket_id = ticket_state.id if ticket_state else existing.ticket_id
            existing.order_number = order_number or existing.order_number
            existing.success = success
            existing.error_message = error_message
            processed_email = existing
        else:
            # Create new record
            processed_email = ProcessedEmail(
                gmail_message_id=gmail_id,
                gmail_thread_id=email_data.get('thread_id'),
                ticket_id=ticket_state.id if ticket_state else None,
                order_number=order_number,
                subject=email_data.get('subject') or '',
                from_address=email_data.get('from', ''),
                message_body=email_data.get('body', ''),
                success=success,
                error_message=error_message
            )
            session.add(processed_email)

        session.commit()

        # Save attachments if present and ticket_state exists
        if success and ticket_state and email_data.get('attachments'):
            self._save_attachments(
                session=session,
                email_data=email_data,
                ticket_state=ticket_state,
                processed_email=processed_email
            )

    def _save_attachments(
        self,
        session: Any,
        email_data: Dict[str, Any],
        ticket_state: TicketState,
        processed_email: ProcessedEmail
    ) -> None:
        """
        Save attachment metadata to database and extract text

        Args:
            session: Database session
            email_data: Email data containing attachments
            ticket_state: Ticket state object
            processed_email: Processed email record
        """
        import os
        from pathlib import Path
        from src.email.text_extractor import TextExtractor

        attachments = email_data.get('attachments', [])
        attachment_texts = email_data.get('attachment_texts', [])
        gmail_id = email_data['id']

        if not attachments:
            return

        text_extractor = TextExtractor()

        for file_path in attachments:
            try:
                # Get file info
                file_path_obj = Path(file_path)
                filename = file_path_obj.name
                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

                # Get mime type
                import mimetypes
                mime_type, _ = mimetypes.guess_type(file_path)

                # Check if attachment already exists
                existing_attachment = session.query(Attachment).filter_by(
                    ticket_id=ticket_state.id,
                    gmail_message_id=gmail_id,
                    filename=filename
                ).first()

                if existing_attachment:
                    logger.debug("Attachment already exists", filename=filename)
                    continue

                # Extract text if supported
                extracted_text = None
                extraction_status = 'pending'
                extraction_error = None

                # Check if text was already extracted (from attachment_texts)
                for att_text in attachment_texts:
                    if att_text.get('filename') == filename:
                        extracted_text = att_text.get('text')
                        extraction_status = 'completed'
                        break

                # If not already extracted, try to extract now
                if not extracted_text:
                    try:
                        extracted_text = text_extractor.extract_text(file_path)
                        if extracted_text:
                            extraction_status = 'completed'
                        else:
                            extraction_status = 'skipped'
                    except Exception as e:
                        logger.warning("Failed to extract text from attachment",
                                     filename=filename,
                                     error=str(e))
                        extraction_status = 'failed'
                        extraction_error = str(e)

                # Create relative path from attachments directory
                # Attachments are stored in attachments/{message_id}/{filename}
                relative_path = f"{gmail_id}/{filename}"

                # Create attachment record
                attachment = Attachment(
                    ticket_id=ticket_state.id,
                    gmail_message_id=gmail_id,
                    processed_email_id=processed_email.id,
                    filename=filename,
                    original_filename=filename,
                    file_path=relative_path,
                    mime_type=mime_type,
                    file_size=file_size,
                    extracted_text=extracted_text,
                    extraction_status=extraction_status,
                    extraction_error=extraction_error
                )

                session.add(attachment)
                logger.info("Saved attachment metadata",
                          filename=filename,
                          ticket_id=ticket_state.ticket_number,
                          extracted_text_length=len(extracted_text) if extracted_text else 0)

            except Exception as e:
                logger.error("Failed to save attachment",
                           file_path=file_path,
                           error=str(e))

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

                # Process any pending retries
                try:
                    retried = self.process_pending_retries()
                    if retried:
                        logger.info("Processed pending retries", count=retried)
                except Exception as e:
                    logger.error("Error processing pending retries", error=str(e))

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

    def _update_ticket_identifiers(
        self,
        session,
        ticket_state: TicketState,
        ticket_data: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> None:
        """Extract and update PO number and supplier references"""
        formatter = MessageFormatter()

        # Extract PO number from ticket data
        if not ticket_state.purchase_order_number:
            po_number = formatter._extract_po_number(ticket_data)
            if po_number:
                ticket_state.purchase_order_number = po_number
                logger.info("Extracted PO number", po_number=po_number, ticket_number=ticket_state.ticket_number)

        # Parse supplier ticket references from history
        ticket_details = ticket_data.get('ticketDetails', [])
        all_refs = set()
        for detail in ticket_details:
            comment = detail.get('comment', '')
            refs = formatter.parse_supplier_references(comment)
            all_refs.update(refs)

        if all_refs:
            refs_str = ','.join(sorted(all_refs))
            if refs_str != ticket_state.supplier_ticket_references:
                ticket_state.supplier_ticket_references = refs_str
                logger.info("Updated supplier references", refs=refs_str, ticket_number=ticket_state.ticket_number)

        # Update supplier email if not set
        if not ticket_state.supplier_email:
            sales_order = ticket_data.get('salesOrder', {})
            pos = sales_order.get('purchaseOrders', [])
            if pos and len(pos) > 0:
                supplier_email = pos[0].get('supplierEmail')
                if supplier_email:
                    ticket_state.supplier_email = supplier_email

        session.flush()

    def _log_ai_decision(
        self,
        session,
        ticket_state: TicketState,
        analysis: Dict[str, Any],
        gmail_message_id: Optional[str] = None
    ) -> Optional[int]:
        """Log AI decision and return decision ID"""
        try:
            decision_log = AIDecisionLog(
                ticket_id=ticket_state.id,
                gmail_message_id=gmail_message_id,
                detected_language=analysis.get('language', 'unknown'),
                detected_intent=analysis.get('intent', 'unknown'),
                confidence_score=analysis.get('confidence', 0.0),
                recommended_action=analysis.get('summary', ''),
                response_generated=str(analysis.get('customer_response', '')),
                action_taken='pending_approval',
                deployment_phase=settings.deployment_phase
            )
            session.add(decision_log)
            session.flush()
            logger.info("AI decision logged", decision_id=decision_log.id, gmail_id=gmail_message_id)
            return decision_log.id
        except Exception as e:
            logger.error("Failed to log AI decision", error=str(e))
            return None

    def _create_pending_messages_from_analysis(
        self,
        session,
        ticket_state: TicketState,
        ticket_data: Dict[str, Any],
        analysis: Dict[str, Any],
        ai_decision_id: Optional[int]
    ) -> None:
        """Create pending messages from AI analysis for human approval"""
        message_service = MessageService(session, self.ticketing_client)
        formatter = MessageFormatter()

        # Parse confidence score from internal note if available
        confidence_score = analysis.get('confidence', 0.5)
        if 'internal_note' in analysis:
            parsed_conf = formatter.parse_confidence_score(analysis['internal_note'])
            if parsed_conf:
                confidence_score = parsed_conf

        # Create customer message if AI generated one
        customer_response = analysis.get('customer_response')
        if customer_response and customer_response.strip() and customer_response.upper() != 'NO_DRAFT':
            try:
                message_service.create_pending_message(
                    ticket_state=ticket_state,
                    message_type='customer',
                    message_body=customer_response,
                    ticket_data=ticket_data,
                    ai_decision_id=ai_decision_id,
                    confidence_score=confidence_score
                )
                logger.info("Created pending customer message", ticket_number=ticket_state.ticket_number)
            except Exception as e:
                logger.error("Failed to create pending customer message", error=str(e))

        # Create supplier message if AI generated one
        supplier_action = analysis.get('supplier_action')
        if supplier_action and isinstance(supplier_action, dict):
            supplier_message = supplier_action.get('message', '')
            if supplier_message and supplier_message.strip() and supplier_message.upper() != 'NO_DRAFT':
                try:
                    message_service.create_pending_message(
                        ticket_state=ticket_state,
                        message_type='supplier',
                        message_body=supplier_message,
                        ticket_data=ticket_data,
                        ai_decision_id=ai_decision_id,
                        confidence_score=confidence_score
                    )
                    logger.info("Created pending supplier message", ticket_number=ticket_state.ticket_number)
                except Exception as e:
                    logger.error("Failed to create pending supplier message", error=str(e))

        # Always create internal note with AI analysis
        internal_note = analysis.get('internal_note') or analysis.get('summary', 'AI Analysis')
        internal_note += f"\n\nConfidence: {confidence_score*100:.0f}%"
        try:
            message_service.create_pending_message(
                ticket_state=ticket_state,
                message_type='internal',
                message_body=internal_note,
                ticket_data=ticket_data,
                ai_decision_id=ai_decision_id,
                confidence_score=confidence_score
            )
            logger.info("Created pending internal note", ticket_number=ticket_state.ticket_number)
        except Exception as e:
            logger.error("Failed to create pending internal note", error=str(e))

        session.flush()
